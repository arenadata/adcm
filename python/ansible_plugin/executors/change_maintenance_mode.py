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
from typing import Any, Collection

from cm.models import Host, MaintenanceMode
from cm.services.status.notify import reset_objects_in_mm
from cm.status_api import send_object_update_event
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.db.transaction import atomic
from pydantic import field_validator

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    CallResult,
    ObjectWithType,
    PluginExecutorConfig,
    RuntimeEnvironment,
    TargetConfig,
    VarsContextSection,
    retrieve_orm_object,
)
from ansible_plugin.errors import PluginIncorrectCallError


class ChangeMaintenanceModeArguments(ObjectWithType):
    value: bool

    @field_validator("type")
    @classmethod
    def check_type_is_allowed(cls, v: str) -> str:
        if v in ("service", "component", "host"):
            return v

        message = f"`adcm_change_maintenance_mode` plugin can't be called to change {v}'s MM"
        raise ValueError(message)


def from_context_based_on_type(
    context_owner: CoreObjectDescriptor,  # noqa: ARG001
    context: VarsContextSection,
    parsed_arguments: Any,
):
    if not isinstance(parsed_arguments, ChangeMaintenanceModeArguments):
        return ()

    return (
        CoreObjectDescriptor(
            id=getattr(context, f"{parsed_arguments.type}_id"), type=ADCMCoreType(parsed_arguments.type)
        ),
    )


class ADCMChangeMMExecutor(ADCMAnsiblePluginExecutor[ChangeMaintenanceModeArguments, None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=ChangeMaintenanceModeArguments),
        target=TargetConfig(detectors=(from_context_based_on_type,)),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: ChangeMaintenanceModeArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[None]:
        _ = runtime

        target, *_ = targets
        target_object = retrieve_orm_object(object_=target)
        value = MaintenanceMode.ON if arguments.value else MaintenanceMode.OFF

        if target_object.maintenance_mode != MaintenanceMode.CHANGING:
            return CallResult(
                value=None,
                changed=False,
                error=PluginIncorrectCallError(
                    f'Only "{MaintenanceMode.CHANGING}" state of object maintenance mode can be changed'
                ),
            )

        with atomic():
            target_object.maintenance_mode = value
            target_object.save(
                update_fields=["maintenance_mode"] if isinstance(target_object, Host) else ["_maintenance_mode"]
            )

        with suppress(Exception):
            send_object_update_event(object_=target_object, changes={"maintenanceMode": target_object.maintenance_mode})

        with suppress(Exception):
            reset_objects_in_mm()

        return CallResult(value=None, changed=True, error=None)
