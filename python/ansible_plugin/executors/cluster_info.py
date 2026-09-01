# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import defaultdict
from collections.abc import Collection
from typing import Any
from uuid import UUID

from cm.models import Cluster, Host, HostComponent, Service
from core.types import CoreObjectDescriptor
from pydantic import field_validator, model_validator
from typing_extensions import Self

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseStrictModel,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
)


class ClusterInfoArguments(BaseStrictModel):
    uuid: UUID | None = None
    name: str | None = None

    @field_validator("uuid", "name", mode="before")
    @classmethod
    def treat_empty_as_unspecified(cls, v: Any) -> str | None:
        # `| default("")` is the natural way to make an argument optional in a playbook,
        # and Ansible passes its own string type
        if v is None or str(v) == "":
            return None

        return str(v)

    @model_validator(mode="after")
    def check_either_is_specified(self) -> Self:
        if self.uuid is None and self.name is None:
            message = "either `uuid` or `name` has to be specified"
            raise ValueError(message)

        return self


class ADCMClusterInfoPluginExecutor(ADCMAnsiblePluginExecutor[ClusterInfoArguments, dict]):
    _config = PluginExecutorConfig(arguments=ArgumentsConfig(represent_as=ClusterInfoArguments))

    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: ClusterInfoArguments, runtime: RuntimeEnvironment
    ) -> CallResult[dict]:
        _ = targets, runtime

        lookup = {"uuid": arguments.uuid} if arguments.uuid is not None else {"name": arguments.name}
        cluster = Cluster.objects.filter(**lookup).first()
        if cluster is None:
            # Not an error: whether this ADCM manages the cluster at all may be
            # exactly what the caller is asking.
            value = {"found": False, "cluster": {}, "hosts": [], "mapping": {}, "services": []}
            return CallResult(value=value, changed=False, error=None)

        mapping = defaultdict(list)
        for fqdn, service_name, component_name in (
            HostComponent.objects.filter(cluster=cluster)
            .order_by("host__fqdn")
            .values_list("host__fqdn", "service__prototype__name", "component__prototype__name")
        ):
            mapping[f"{service_name}.{component_name}"].append(fqdn)

        value = {
            "found": True,
            "cluster": {
                "id": cluster.id,
                "name": cluster.name,
                "uuid": str(cluster.uuid),
                "state": cluster.state,
            },
            "hosts": sorted(Host.objects.filter(cluster=cluster).values_list("fqdn", flat=True)),
            "mapping": dict(mapping),
            "services": sorted(Service.objects.filter(cluster=cluster).values_list("prototype__name", flat=True)),
        }

        return CallResult(value=value, changed=False, error=None)
