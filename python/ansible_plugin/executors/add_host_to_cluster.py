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

from cm.models import Host
from cm.services.cluster import perform_host_to_cluster_map
from cm.services.status import notify
from core.types import ADCMCoreType, CoreObjectDescriptor
from pydantic import BaseModel, model_validator
from typing_extensions import Self

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    AnsibleJobContext,
    ArgumentsConfig,
    CallResult,
    ContextConfig,
    PluginExecutorConfig,
)
from ansible_plugin.errors import PluginRuntimeError, PluginValidationError


class AddHostToClusterArguments(BaseModel):
    fqdn: str | None = None
    host_id: int | None = None

    @model_validator(mode="after")
    def check_either_is_specified(self) -> Self:
        # won't filter out empty strings or 0 `host_id`, leave it to plugin logic to handle
        if self.fqdn is None and self.host_id is None:
            message = "either `fqdn` or `host_id` have to be specified"
            raise ValueError(message)

        return self


def cluster_id_must_be_in_context(
    context_owner: CoreObjectDescriptor, context: AnsibleJobContext
) -> PluginValidationError | None:
    _ = context_owner

    return (
        None
        if context.cluster_id
        else PluginValidationError(message="Expected `cluster_id` in context, but it's missing")
    )


class ADCMAddHostToClusterPluginExecutor(ADCMAnsiblePluginExecutor[AddHostToClusterArguments, None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=AddHostToClusterArguments),
        context=ContextConfig(
            allow_only=frozenset((ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT)),
            validators=(cluster_id_must_be_in_context,),
        ),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: AddHostToClusterArguments,
        context_owner: CoreObjectDescriptor,
        context: AnsibleJobContext,
    ) -> CallResult[None]:
        _ = targets, context_owner

        host_id = arguments.host_id
        if arguments.fqdn is not None:
            try:
                host_id = Host.objects.values_list("id", flat=True).get(fqdn=arguments.fqdn)
            except Host.DoesNotExist:
                return CallResult(
                    value=None,
                    changed=False,
                    error=PluginRuntimeError(message=f'Failed to locate host with fqdn "{arguments.fqdn}"'),
                )

        if host_id is None:
            # at this point it can't be None due to validation => raising instead of returning
            raise PluginRuntimeError(message="Failed to detect what host to add")

        perform_host_to_cluster_map(cluster_id=context.cluster_id, hosts=[host_id], status_service=notify)

        return CallResult(value=None, changed=True, error=None)
