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

from cm.api import delete_service, save_hc
from cm.models import ClusterBind, ClusterObject, HostComponent
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.db.transaction import atomic
from pydantic import BaseModel

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    AnsibleJobContext,
    ArgumentsConfig,
    CallResult,
    ContextConfig,
    PluginExecutorConfig,
)
from ansible_plugin.errors import PluginRuntimeError, PluginTargetDetectionError


class DeleteServiceArguments(BaseModel):
    service: str | None = None


class ADCMDeleteServicePluginExecutor(ADCMAnsiblePluginExecutor[DeleteServiceArguments, None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=DeleteServiceArguments),
        context=ContextConfig(allow_only=frozenset((ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE))),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: DeleteServiceArguments,
        context_owner: CoreObjectDescriptor,
        context: AnsibleJobContext,
    ) -> CallResult[None]:
        _ = targets

        if arguments.service:
            search_kwargs = {"cluster_id": context.cluster_id, "prototype__name": arguments.service}
        elif context_owner.type == ADCMCoreType.SERVICE:
            search_kwargs = {"id": context_owner.id}
        else:
            message = f"Incorrect plugin call for {arguments.service=} in context {context_owner}"
            raise PluginRuntimeError(message)

        try:
            service = ClusterObject.objects.select_related("cluster").get(**search_kwargs)
        except ClusterObject.DoesNotExist:
            return CallResult(
                value=None, changed=False, error=PluginTargetDetectionError("Failed to locate service to be deleted")
            )

        with atomic():
            # clean up hc
            new_hc_list = [
                (hostcomponent.service, hostcomponent.host, hostcomponent.component)
                for hostcomponent in HostComponent.objects.filter(cluster=service.cluster)
                .exclude(service=service)
                .select_related("host", "service", "component")
                .order_by("id")
            ]
            save_hc(service.cluster, new_hc_list)

            # remove existing binds
            ClusterBind.objects.filter(source_service=service).delete()

            # perform service deletion
            delete_service(service=service)

        return CallResult(value=None, changed=True, error=None)
