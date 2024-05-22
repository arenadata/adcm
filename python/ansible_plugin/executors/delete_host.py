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

from cm.api import delete_host
from cm.models import Host
from core.types import ADCMCoreType, CoreObjectDescriptor

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    CallResult,
    ContextConfig,
    NoArguments,
    PluginExecutorConfig,
    RuntimeEnvironment,
)
from ansible_plugin.errors import PluginTargetDetectionError


class ADCMDeleteHostPluginExecutor(ADCMAnsiblePluginExecutor[NoArguments, None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=NoArguments),
        context=ContextConfig(allow_only=frozenset({ADCMCoreType.HOST})),
    )

    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: NoArguments, runtime: RuntimeEnvironment
    ) -> CallResult[None]:
        _ = targets, arguments

        try:
            delete_host(Host.obj.get(pk=runtime.context_owner.id), cancel_tasks=False)
        except Host.DoesNotExist:
            return CallResult(
                value=None,
                changed=False,
                error=PluginTargetDetectionError(message=f"Host #{runtime.context_owner.id} wasn't found"),
            )

        return CallResult(value=None, changed=True, error=None)
