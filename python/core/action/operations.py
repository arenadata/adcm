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

from collections.abc import Iterable, Iterator
from enum import Enum
from typing import Literal, TypeAlias

from core.action._types import JobSpec, ScriptType
from core.cluster import ClusterTopology
from core.cluster._operations import find_children
from core.config import Attributes
from core.result import Fail, Success
from core.types import (
    ADCMCoreType,
    ClusterDesc,
    ComponentDesc,
    HostDesc,
    MaintenanceModeOfObjects,
    MaintenanceModeState,
    ServiceDesc,
)

StartImpossibleReason: TypeAlias = str


class ActionStartImpossibleReason(str, Enum):
    LDAP_OFF = "The Action is not available. You need to fill in the LDAP integration settings."
    MAINTENANCE_MODE = 'The {entity_type} is not available. One or more {violator_type} in "Maintenance mode"'


def has_bundle_revert_script(scripts: Iterable[JobSpec]) -> bool:
    return any(script.script_type == ScriptType.INTERNAL and script.script == "bundle_revert" for script in scripts)


def detect_start_impossible_reason_for_adcm(
    ldap_integration_attr: Attributes,
) -> Success[None] | Fail[Literal[ActionStartImpossibleReason.LDAP_OFF]]:
    if not ldap_integration_attr.is_active:
        return Fail(ActionStartImpossibleReason.LDAP_OFF)

    return Success(None)


def detect_start_impossible_reason_for_cluster_objects(
    target: ClusterDesc | ServiceDesc | ComponentDesc,
    topology: ClusterTopology,
    maintenance_mode: MaintenanceModeOfObjects,
) -> Success[None] | Fail[tuple[Literal[ActionStartImpossibleReason.MAINTENANCE_MODE], ADCMCoreType]]:
    in_mm = _get_objects_with_not_off_mm(mm_objects=maintenance_mode)
    children = set(find_children(target=target, topology=topology))
    affected = {target, *children}.intersection(in_mm)

    if not affected:
        return Success(None)

    affected_types = {desc.type for desc in affected}
    for type_ in (ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT, ADCMCoreType.HOST):  # error messages priority
        if type_ in affected_types:
            return Fail((ActionStartImpossibleReason.MAINTENANCE_MODE, type_))

    return Success(None)


def detect_start_impossible_reason_for_provider_objects(
    maintenance_mode: MaintenanceModeOfObjects,
) -> Success[None] | Fail[tuple[Literal[ActionStartImpossibleReason.MAINTENANCE_MODE], ADCMCoreType]]:
    in_mm = _get_objects_with_not_off_mm(mm_objects=maintenance_mode)
    if violator := next(in_mm, None):
        return Fail((ActionStartImpossibleReason.MAINTENANCE_MODE, violator.type))

    return Success(None)


def _get_objects_with_not_off_mm(
    mm_objects: MaintenanceModeOfObjects,
) -> Iterator[ServiceDesc | ComponentDesc | HostDesc]:
    return (desc for desc, mm in mm_objects.objects_dict.items() if mm != MaintenanceModeState.OFF)
