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

from collections.abc import Collection
from typing import NamedTuple, TypeVar

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    CallArguments,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
)
from core.types import CoreObjectDescriptor

Executor = TypeVar("Executor", bound=ADCMAnsiblePluginExecutor)


class PassedArguments(NamedTuple):
    targets: Collection[CoreObjectDescriptor]
    arguments: CallArguments
    runtime: RuntimeEnvironment


def DummyExecutor(  # noqa: N802
    config: PluginExecutorConfig[CallArguments],
) -> type[ADCMAnsiblePluginExecutor[CallArguments, PassedArguments]]:
    class DummyExecutorWithConfig(ADCMAnsiblePluginExecutor):
        _config: PluginExecutorConfig[CallArguments] = config

        def __call__(
            self, targets: Collection[CoreObjectDescriptor], arguments: CallArguments, runtime: RuntimeEnvironment
        ) -> CallResult[PassedArguments]:
            return CallResult(
                value=PassedArguments(targets=targets, arguments=arguments, runtime=runtime),
                changed=True,
                error=None,
            )

    return DummyExecutorWithConfig
