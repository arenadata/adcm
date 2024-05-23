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

from cm.converters import core_type_to_model
from cm.status_api import send_object_update_event
from core.types import CoreObjectDescriptor
from django.db.models import ObjectDoesNotExist
from pydantic import BaseModel

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
    TargetConfig,
    from_arguments_root,
)
from ansible_plugin.errors import PluginTargetDetectionError
from ansible_plugin.executors._validators import validate_target_allowed_for_context_owner, validate_type_is_present


class ChangeStateArguments(BaseModel):
    state: str


class ChangeStateReturnValue(TypedDict):
    state: str


class ADCMStatePluginExecutor(ADCMAnsiblePluginExecutor[ChangeStateArguments, ChangeStateReturnValue]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=ChangeStateArguments),
        target=TargetConfig(detectors=(from_arguments_root,), validators=(validate_type_is_present,)),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: ChangeStateArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[ChangeStateReturnValue]:
        target, *_ = targets

        if error := validate_target_allowed_for_context_owner(context_owner=runtime.context_owner, target=target):
            return CallResult(value={}, changed=False, error=error)

        try:
            target_object = core_type_to_model(core_type=target.type).objects.get(pk=target.id)
        except ObjectDoesNotExist:
            return CallResult(
                value=None,
                changed=False,
                error=PluginTargetDetectionError(message=f'Failed to locate {target.type} with id "{target.id}"'),
            )

        target_object.set_state(state=arguments.state)

        with suppress(Exception):
            send_object_update_event(object_=target, changes={"state": arguments.state})

        return CallResult(value=ChangeStateReturnValue(state=arguments.state), changed=True, error=None)
