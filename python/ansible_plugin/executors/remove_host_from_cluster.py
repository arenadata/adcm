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

from cm.api import remove_host_from_cluster
from cm.models import Host
from core.types import ADCMCoreType, CoreObjectDescriptor
from pydantic import BaseModel, model_validator
from typing_extensions import Self

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    CallResult,
    ContextConfig,
    PluginExecutorConfig,
    RuntimeEnvironment,
)
from ansible_plugin.errors import (
    PluginRuntimeError,
    PluginTargetDetectionError,
)


class RemoveHostFromClusterArguments(BaseModel):
    fqdn: str | None = None
    host_id: int | None = None

    @model_validator(mode="after")
    def check_either_is_specified(self) -> Self:
        # won't filter out empty strings or 0 `host_id`, leave it to plugin logic to handle
        if self.fqdn is None and self.host_id is None:
            message = "either `fqdn` or `host_id` have to be specified"
            raise ValueError(message)

        return self


class ADCMRemoveHostFromClusterPluginExecutor(ADCMAnsiblePluginExecutor[RemoveHostFromClusterArguments, None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=RemoveHostFromClusterArguments),
        context=ContextConfig(allow_only=frozenset((ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE))),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: RemoveHostFromClusterArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[None]:
        _ = targets

        # eventually would be better to set explicit restriction to arguments - either on id or one fqdn
        # for now, we'll leave it as it is in order to support old behavior
        search_kwargs = {"fqdn": arguments.fqdn} if arguments.fqdn else {"id": arguments.host_id}

        try:
            host = Host.obj.select_related("cluster").get(**search_kwargs)
        except Host.DoesNotExist:
            return CallResult(
                value=None,
                changed=False,
                error=PluginTargetDetectionError(message=f"Can't find host by given arguments: {arguments=}"),
            )

        if not host.cluster_id:
            return CallResult(
                value=None,
                changed=False,
                error=PluginRuntimeError(message=f"Host {host.fqdn} is unbound to any cluster"),
            )
        elif host.cluster_id != runtime.vars.context.cluster_id:
            return CallResult(
                value=None,
                changed=False,
                error=PluginRuntimeError(
                    message=f"Host {host.fqdn} is not in cluster id: {runtime.vars.context.cluster_id}"
                ),
            )
        remove_host_from_cluster(host)

        return CallResult(value=None, changed=True, error=None)
