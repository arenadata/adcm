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
from typing import Collection, TypedDict

from cm.converters import orm_object_to_core_type
from cm.status_api import send_object_update_event
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
from ansible_plugin.errors import PluginRuntimeError
from ansible_plugin.executors._validators import validate_target_allowed_for_context_owner


class MultiStateUnsetArguments(BaseTypedArguments):
    state: str
    missing_ok: bool = False


class MultiStateUnsetReturnValue(TypedDict):
    state: str


class ADCMMultiStateUnsetPluginExecutor(
    ADCMAnsiblePluginExecutor[MultiStateUnsetArguments, MultiStateUnsetReturnValue]
):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=MultiStateUnsetArguments),
        target=TargetConfig(detectors=(from_arguments_root,)),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: MultiStateUnsetArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[MultiStateUnsetReturnValue]:
        target, *_ = targets

        if error := validate_target_allowed_for_context_owner(context_owner=runtime.context_owner, target=target):
            return CallResult(value=None, changed=False, error=error)

        target_object = retrieve_orm_object(object_=target)

        if not arguments.missing_ok and arguments.state not in target_object.multi_state:
            raise PluginRuntimeError(
                f'Can not delete missing multi-state "{arguments.state}". '
                f'Set missing_ok to "True" or choose an existing multi-state'
            )

        target_object.unset_multi_state(arguments.state)
        with suppress(Exception):
            send_object_update_event(
                obj_id=target_object.pk,
                obj_type=orm_object_to_core_type(target_object).value,
                changes={"state": arguments.state},
            )

        return CallResult(value=MultiStateUnsetReturnValue(state=arguments.state), changed=True, error=None)
