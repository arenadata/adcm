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
from contextlib import suppress
from typing import TypedDict

from cm.transition.status import StatusScenarios
from core.locks import LockRepoI
from core.object.repo import ObjectRepoI
from core.types import CoreObjectDescriptor
from django.db.transaction import atomic

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseTypedArguments,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
    TargetConfig,
    from_arguments_root,
)
from ansible_plugin.executors._validators import validate_target_allowed_for_context_owner


class StateArguments(BaseTypedArguments):
    state: str


class StateReturnValue(TypedDict):
    state: str


class ADCMStatePluginExecutor(ADCMAnsiblePluginExecutor[StateArguments, StateReturnValue]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=StateArguments),
        target=TargetConfig(detectors=(from_arguments_root,)),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: StateArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[StateReturnValue]:
        target, *_ = targets

        if error := validate_target_allowed_for_context_owner(context_owner=runtime.context_owner, target=target):
            return CallResult(value=None, changed=False, error=error)

        with atomic():
            self._container.get(LockRepoI).register_lock_on_object_waiting(target=target, aspect="state")
            self._container.get(ObjectRepoI).set_state(object_=target, state=arguments.state)

        status_scenarios = self._container.get(StatusScenarios)
        with suppress(Exception):
            status_scenarios.send_object_update_event(
                obj_id=target.id,
                obj_type=target.type.value,
                changes={"state": arguments.state},
            )

        return CallResult(value=StateReturnValue(state=arguments.state), changed=True, error=None)
