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

from typing import Any, Collection, Literal

from cm.api import get_hc
from cm.models import Cluster, Host, JobLog, ServiceComponent
from cm.services.mapping import change_host_component_mapping
from core.cluster.types import HostComponentEntry
from core.types import ADCMCoreType, CoreObjectDescriptor
from pydantic import field_validator

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseStrictModel,
    CallResult,
    ContextConfig,
    PluginExecutorConfig,
    RuntimeEnvironment,
    VarsContextSection,
)
from ansible_plugin.errors import PluginIncorrectCallError, PluginRuntimeError, PluginValidationError


class Operation(BaseStrictModel):
    action: Literal["add", "remove"]
    service: str
    component: str
    host: str

    @field_validator("action", mode="before")
    @classmethod
    def convert_action_to_string(cls, v: Any) -> str:
        # requited to pre-process Ansible Strings
        return str(v)


class ChangeHostComponentArguments(BaseStrictModel):
    operations: list[Operation]


def cluster_id_must_be_in_context(
    context_owner: CoreObjectDescriptor, context: VarsContextSection
) -> PluginValidationError | None:
    _ = context_owner

    return (
        None
        if context.cluster_id
        else PluginValidationError(message="Expected `cluster_id` in context, but it's missing")
    )


class ADCMHostComponentPluginExecutor(ADCMAnsiblePluginExecutor[ChangeHostComponentArguments, None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=ChangeHostComponentArguments),
        context=ContextConfig(
            allow_only=frozenset((ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT)),
            validators=(cluster_id_must_be_in_context,),
        ),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: ChangeHostComponentArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[None]:
        _ = targets

        action_hc_map = (
            JobLog.objects.values_list("task__action__hostcomponentmap", flat=True)
            .filter(id=runtime.vars.job.id)
            .first()
        )
        if action_hc_map:
            raise PluginIncorrectCallError(message="You can not change hc in plugin for action with hc_acl")

        cluster = Cluster.objects.get(id=runtime.vars.context.cluster_id)

        hostcomponent = get_hc(cluster)
        for operation in arguments.operations:
            component_id, service_id = ServiceComponent.objects.values_list("id", "service_id").get(
                cluster=cluster, service__prototype__name=operation.service, prototype__name=operation.component
            )
            host_id = Host.objects.values_list("id", flat=True).get(cluster=cluster, fqdn=operation.host)
            item = {
                "host_id": host_id,
                "service_id": service_id,
                "component_id": component_id,
            }
            if operation.action == "add":
                if item in hostcomponent:
                    return CallResult(
                        value=None,
                        changed=False,
                        error=PluginRuntimeError(
                            message=f'There is already component "{operation.component}" on host "{operation.host}"'
                        ),
                    )

                hostcomponent.append(item)

            else:
                if item not in hostcomponent:
                    return CallResult(
                        value=None,
                        changed=False,
                        error=PluginRuntimeError(
                            message=f'There is no component "{operation.component}" on host "{operation.host}"'
                        ),
                    )

                hostcomponent.remove(item)

        change_host_component_mapping(
            cluster_id=cluster.id,
            bundle_id=cluster.prototype.bundle_id,
            flat_mapping=(
                HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"])
                for entry in hostcomponent
            ),
        )

        return CallResult(value=None, changed=True, error=None)
