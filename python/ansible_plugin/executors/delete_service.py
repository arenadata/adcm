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

from typing import Collection

from cm.api import delete_service
from cm.models import ClusterBind, Service, HostComponent, Prototype
from cm.services.mapping import change_host_component_mapping, check_nothing
from core.cluster.types import HostComponentEntry
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.db.transaction import atomic

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseStrictModel,
    CallResult,
    ContextConfig,
    PluginExecutorConfig,
    RuntimeEnvironment,
)
from ansible_plugin.errors import PluginIncorrectCallError, PluginRuntimeError, PluginTargetDetectionError


class DeleteServiceArguments(BaseStrictModel):
    service: str | None = None


class ADCMDeleteServicePluginExecutor(ADCMAnsiblePluginExecutor[DeleteServiceArguments, None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=DeleteServiceArguments),
        context=ContextConfig(allow_only=frozenset((ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE))),
    )

    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: DeleteServiceArguments, runtime: RuntimeEnvironment
    ) -> CallResult[None]:
        _ = targets

        if arguments.service is not None:
            if runtime.context_owner.type == ADCMCoreType.SERVICE:
                message = (
                    "Service can be deleted by name only from cluster's context. "
                    "To delete caller-service don't specify `service` argument."
                )
                raise PluginIncorrectCallError(message)

            search_kwargs = {"cluster_id": runtime.vars.context.cluster_id, "prototype__name": arguments.service}
        elif runtime.context_owner.type == ADCMCoreType.SERVICE:
            search_kwargs = {"id": runtime.context_owner.id}
        else:
            message = f"Incorrect plugin call for {arguments.service=} in context {runtime.context_owner}"
            raise PluginRuntimeError(message)

        try:
            service = Service.objects.select_related("cluster").get(**search_kwargs)
        except Service.DoesNotExist:
            return CallResult(
                value=None, changed=False, error=PluginTargetDetectionError("Failed to locate service to be deleted")
            )

        with atomic():
            bundle_id = Prototype.objects.values_list("bundle_id", flat=True).get(id=service.prototype_id)
            change_host_component_mapping(
                cluster_id=service.cluster_id,
                bundle_id=bundle_id,
                flat_mapping=(
                    HostComponentEntry(**entry)
                    for entry in HostComponent.objects.values("host_id", "component_id")
                    .filter(cluster=service.cluster)
                    .exclude(service=service)
                ),
                checks_func=check_nothing,
            )

            # remove existing binds
            ClusterBind.objects.filter(source_service=service).delete()

            # perform service deletion
            delete_service(service=service)

        return CallResult(value=None, changed=True, error=None)
