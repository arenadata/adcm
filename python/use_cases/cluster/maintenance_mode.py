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

from dataclasses import dataclass
from typing import Literal, TypeAlias, cast

from cm.converters import orm_object_to_core_type
from cm.models import Action, Component, Host, Service
from cm.transition.status import StatusScenarios
from core.cluster import ClusterService, ClusterTopology
from core.constants import (
    ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
    ADCM_HOST_TURN_ON_MM_ACTION_NAME,
    ADCM_TURN_OFF_MM_ACTION_NAME,
    ADCM_TURN_ON_MM_ACTION_NAME,
)
from core.types import (
    ADCMCoreType,
    ComponentDesc,
    Descriptor,
    HostDesc,
    MaintenanceModeState,
    MMReason,
    ObjectMM,
    ServiceDesc,
)
from django.db.transaction import atomic

from use_cases.dto import RunActionDTO
from use_cases.transition.job.schedule import ScheduleMMChangingTask

MMTargetORM: TypeAlias = Service | Component | Host
MMTarget: TypeAlias = ServiceDesc | ComponentDesc | HostDesc


class MaintenanceModeError(Exception):
    ...


class MMIsNotAvailableError(MaintenanceModeError):
    ...


class MMIsChangingError(MaintenanceModeError):
    ...


class MMValueError(MaintenanceModeError):
    ...


@dataclass(slots=True)
class SetMaintenanceMode:
    cluster_service: ClusterService
    status_scenarios: StatusScenarios
    schedule_task: ScheduleMMChangingTask

    def do(
        self, target: MMTargetORM, value: Literal[MaintenanceModeState.ON, MaintenanceModeState.OFF]
    ) -> MaintenanceModeState:
        with atomic():
            if not (cluster_id := target.cluster_id):  # pyright: ignore[reportAttributeAccessIssue]
                raise MMIsNotAvailableError("Maintenance mode is not available")

            target_type = orm_object_to_core_type(target)
            if not target.cluster.prototype.allow_maintenance_mode:
                raise MMIsNotAvailableError(f"{target_type.value.capitalize()} does not support maintenance mode")

            topology = self.cluster_service.retrieve_topology(cluster_id=cluster_id)
            own_mm = self.cluster_service.retrieve_own_maintenance_mode(cluster_ids=(cluster_id,))
            calculated_mm = self.cluster_service.calculate_maintenance_mode(topology=topology, objects_own_mm=own_mm)

            target_descriptor = cast(ServiceDesc | ComponentDesc | HostDesc, Descriptor(id=target.pk, type=target_type))
            prototype_orm = target.prototype
            action_extra_filter = {}

            match target_descriptor.type:
                case ADCMCoreType.SERVICE:
                    target_own_mm = own_mm.services[target_descriptor.id]
                    target_calculated_mm = calculated_mm.services[target_descriptor.id]
                case ADCMCoreType.COMPONENT:
                    target_own_mm = own_mm.components[target_descriptor.id]
                    target_calculated_mm = calculated_mm.components[target_descriptor.id]
                case ADCMCoreType.HOST:
                    target_own_mm = own_mm.hosts[target_descriptor.id]
                    target_calculated_mm = calculated_mm.hosts[target_descriptor.id]
                    prototype_orm = target.cluster.prototype
                    action_extra_filter = {"host_action": True}

            _check_mm_status(
                target=target_descriptor,
                own_mm=target_own_mm,
                calculated_mm_reason=target_calculated_mm.reason,
                value=value,
            )

            mapping_exists = False
            mm_action_name = _pick_mm_action_name(target=target_descriptor, value=value)
            try:
                action = Action.objects.filter(
                    prototype=prototype_orm, name=mm_action_name, **action_extra_filter
                ).get()
                mapping_exists = _is_mapping_exists(target=target_descriptor, topology=topology)
            except Action.DoesNotExist:
                action = None

            return_value = value
            if action is not None and (mapping_exists or target_descriptor.type == ADCMCoreType.HOST):
                return_value = MaintenanceModeState.CHANGING

                self.schedule_task.do(action_orm=action, target=target, payload=RunActionDTO())
                self.cluster_service.repo.set_maintenance_mode(target=target_descriptor, value=return_value)
            else:
                self.cluster_service.repo.set_maintenance_mode(target=target_descriptor, value=value)

        self.status_scenarios.update_mm_objects()
        self.status_scenarios.send_object_update_event(
            obj_id=target_descriptor.id, obj_type=target_descriptor.type.value, changes={"maintenanceMode": value.value}
        )

        return return_value


def _pick_mm_action_name(target: MMTarget, value: Literal[MaintenanceModeState.ON, MaintenanceModeState.OFF]) -> str:
    match value, target.type:
        case (MaintenanceModeState.ON, ADCMCoreType.HOST):
            return ADCM_HOST_TURN_ON_MM_ACTION_NAME
        case (MaintenanceModeState.ON, _):
            return ADCM_TURN_ON_MM_ACTION_NAME
        case (MaintenanceModeState.OFF, ADCMCoreType.HOST):
            return ADCM_HOST_TURN_OFF_MM_ACTION_NAME
        case (MaintenanceModeState.OFF, _):
            return ADCM_TURN_OFF_MM_ACTION_NAME


def _is_mapping_exists(target: MMTarget, topology: ClusterTopology) -> bool:
    match target.type:
        case ADCMCoreType.SERVICE:
            return bool(next(topology.services[target.id].host_ids, None))
        case ADCMCoreType.COMPONENT:
            component = topology.get_component(target.id)
            return bool(component.hosts)
        case ADCMCoreType.HOST:
            return target.id not in topology.unmapped_hosts


def _check_mm_status(
    target: MMTarget,
    own_mm: ObjectMM,
    calculated_mm_reason: MMReason,
    value: Literal[MaintenanceModeState.ON, MaintenanceModeState.OFF],
) -> None:
    """
    Here we check user input (value) against EXPLICIT object's MM (own_mm).
    It is forbidden to:
        1. Manipulate with objects in CHANGING state
        2. Setting the same value as object's explicit MM
            In case of disabling already disabled MM,
            it is necessary to clarify the source of this MM (calculated_mm_reason)
    """

    if own_mm == MaintenanceModeState.CHANGING:
        raise MMIsChangingError("Maintenance mode is changing now")

    if own_mm == MaintenanceModeState.OFF and value == MaintenanceModeState.OFF:
        error_desc = _build_disable_mm_error_response_description(reason=calculated_mm_reason, object_type=target.type)
        raise MMValueError(error_desc)

    if own_mm == MaintenanceModeState.ON and value == MaintenanceModeState.ON:
        raise MMValueError("Maintenance mode already on")


def _build_disable_mm_error_response_description(reason: MMReason, object_type: ADCMCoreType) -> str:
    template = (
        "The {object_type} is in maintenance mode because {mm_source} in maintenance mode. "
        "To turn it off, disable maintenance mode on related {mm_source_type}."
    )

    match reason:
        case MMReason.ALL_HOSTS_IN_MM if object_type in {ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}:
            mm_source = "the hosts where it is installed are"
            mm_source_type = "hosts"
        case MMReason.ALL_COMPONENTS_IN_MM if object_type == ADCMCoreType.SERVICE:
            mm_source = "all it's components are"
            mm_source_type = "components"
        case MMReason.SERVICE_IN_MM if object_type == ADCMCoreType.COMPONENT:
            mm_source = "it's service is"
            mm_source_type = "service"
        case MMReason.SELF:
            return "Maintenance mode already off."
        case _:
            raise NotImplementedError(f"Unknown {reason=} for {object_type=}")

    return template.format(object_type=object_type.value, mm_source=mm_source, mm_source_type=mm_source_type)
