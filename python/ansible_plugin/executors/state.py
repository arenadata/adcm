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

from contextlib import suppress
from typing import Collection

from cm.status_api import send_object_update_event
from core.types import CoreObjectDescriptor

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
    SingleStateArgument,
    SingleStateReturnValue,
    TargetConfig,
    from_arguments_root,
    retrieve_orm_object,
)
from ansible_plugin.executors._validators import validate_target_allowed_for_context_owner, validate_type_is_present


class ADCMStatePluginExecutor(ADCMAnsiblePluginExecutor[SingleStateArgument, SingleStateReturnValue]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=SingleStateArgument),
        target=TargetConfig(detectors=(from_arguments_root,), validators=(validate_type_is_present,)),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: SingleStateArgument,
        runtime: RuntimeEnvironment,
    ) -> CallResult[SingleStateReturnValue]:
        target, *_ = targets

        if error := validate_target_allowed_for_context_owner(context_owner=runtime.context_owner, target=target):
            return CallResult(value=None, changed=False, error=error)

        target_object = retrieve_orm_object(object_=target)
        target_object.set_state(state=arguments.state)
        with suppress(Exception):
            send_object_update_event(object_=target_object, changes={"state": arguments.state})

        return CallResult(value=SingleStateReturnValue(state=arguments.state), changed=True, error=None)
