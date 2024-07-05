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

from typing import Collection, TypedDict

from core.types import CoreObjectDescriptor

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseTypedArguments,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
    TargetConfig,
    from_arguments_root,
    retrieve_orm_object,
)
from ansible_plugin.executors._validators import validate_target_allowed_for_context_owner


class MultiStateSetArguments(BaseTypedArguments):
    state: str


class MultiStateSetReturnValue(TypedDict):
    state: str


class ADCMMultiStateSetPluginExecutor(ADCMAnsiblePluginExecutor[MultiStateSetArguments, MultiStateSetReturnValue]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=MultiStateSetArguments),
        target=TargetConfig(detectors=(from_arguments_root,)),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: MultiStateSetArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[MultiStateSetReturnValue]:
        target, *_ = targets

        if error := validate_target_allowed_for_context_owner(context_owner=runtime.context_owner, target=target):
            return CallResult(value=None, changed=False, error=error)

        target_object = retrieve_orm_object(object_=target)
        target_object.set_multi_state(arguments.state)

        return CallResult(value=MultiStateSetReturnValue(state=arguments.state), changed=True, error=None)
