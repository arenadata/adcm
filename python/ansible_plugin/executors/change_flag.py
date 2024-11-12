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

from enum import Enum
from typing import Collection

from cm.services.concern.flags import (
    BuiltInFlag,
    ConcernFlag,
    lower_all_flags,
    lower_flag,
    raise_flag,
    update_hierarchy_for_flag,
)
from cm.status_api import notify_about_redistributed_concerns_from_maps
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.db.transaction import atomic
from pydantic import field_validator

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseArgumentsWithTypedObjects,
    CallResult,
    PluginExecutorConfig,
    ReturnValue,
    RuntimeEnvironment,
    TargetConfig,
    VarsContextSection,
    from_context,
    from_objects,
)
from ansible_plugin.errors import PluginRuntimeError, PluginValidationError


class ChangeFlagOperation(str, Enum):
    UP = "up"
    DOWN = "down"


class ChangeFlagArguments(BaseArgumentsWithTypedObjects):
    operation: ChangeFlagOperation
    name: str | None = None
    msg: str = ""

    @field_validator("name")
    @classmethod
    def check_name_length(cls, v: str | None) -> str | None:
        if v is None:
            return v

        if len(v) < 1:
            message = "`name` should be at least 1 symbol"
            raise ValueError(message)

        return v


def validate_objects(
    context_owner: CoreObjectDescriptor,
    context: VarsContextSection,  # noqa: ARG001
    raw_arguments: dict,
) -> PluginValidationError | None:
    match context_owner.type:
        case ADCMCoreType.PROVIDER | ADCMCoreType.HOST:
            if "objects" in raw_arguments:
                return PluginValidationError(message=f"`objects` shouldn't be specified for {context_owner.type}")
        case ADCMCoreType.CLUSTER | ADCMCoreType.SERVICE | ADCMCoreType.COMPONENT:
            objects_ = raw_arguments.get("objects")
            if objects_ is not None:
                if not isinstance(objects_, list) or not all(isinstance(entry, dict) for entry in objects_):
                    return PluginValidationError(message="`objects` should be of `list[dict]` type")

                allowed_types = ("cluster", "service", "component")
                if any(entry.get("type") not in allowed_types for entry in objects_):
                    return PluginValidationError(message=f"`objects` can only be one of: {', '.join(allowed_types)}")

    return None


def validate_name_and_message_correct_for_operation(arguments: ChangeFlagArguments) -> PluginValidationError | None:
    if arguments.operation == ChangeFlagOperation.DOWN:
        return None

    if not arguments.name:
        return PluginValidationError(f"`name` should be specified for `{ChangeFlagOperation.UP.value}` operation")


class ADCMChangeFlagPluginExecutor(ADCMAnsiblePluginExecutor[ChangeFlagArguments, None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(
            represent_as=ChangeFlagArguments, validators=(validate_name_and_message_correct_for_operation,)
        ),
        target=TargetConfig(detectors=(from_objects, from_context), validators=(validate_objects,)),
    )

    @atomic()
    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: ChangeFlagArguments, runtime: RuntimeEnvironment
    ) -> CallResult[ReturnValue]:
        _ = runtime

        match arguments.operation:
            case ChangeFlagOperation.UP:
                built_in_flag = BuiltInFlag.__members__.get(arguments.name.upper())
                if built_in_flag:
                    flag = built_in_flag.value
                    if arguments.msg:
                        flag = ConcernFlag(name=flag.name, message=arguments.msg, cause=flag.cause)
                else:
                    flag = ConcernFlag(name=arguments.name.lower(), message=arguments.msg, cause=None)

                changed = raise_flag(flag=flag, on_objects=targets)
                if changed:
                    added = update_hierarchy_for_flag(flag=flag, on_objects=targets)
                    notify_about_redistributed_concerns_from_maps(added=added, removed={})
            case ChangeFlagOperation.DOWN:
                if arguments.name:
                    changed = lower_flag(name=arguments.name.lower(), on_objects=targets)
                else:
                    changed = lower_all_flags(on_objects=targets)
            case _:
                message = f"Can't handle operation {arguments.operation}"
                raise PluginRuntimeError(message=message)

        return CallResult(value={}, changed=changed, error=None)
