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

from core.action.types import JobHierarchyLevel, JobShortInfo, JobSpecV1, RichJob, ScriptType
from core.cluster import ClusterTopology
from core.cluster._operations import find_children
from core.config import Attributes
from core.result import Fail, Success
from core.spec.keys import level_keys_to_full_key
from core.spec.types import FullSpecKey, LevelSpecKey
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


def to_rich_job(spec: JobSpecV1, job: JobShortInfo) -> RichJob:
    """
    Pair a job with the plan node it was created for.

    The plan says what the task consists of, so a job pointing at a node that isn't in it
    is a job that shouldn't exist, not a node to be invented.
    """

    try:
        script_spec = spec.scripts[job.spec_key]
    except KeyError as err:
        message = f"Execution plan has no {job.spec_key} job #{job.id} is made of"
        raise KeyError(message) from err

    return RichJob(spec=script_spec, runtime=job)


def to_rich_jobs(spec: JobSpecV1, jobs: Iterable[JobShortInfo]) -> dict[FullSpecKey, RichJob]:
    """
    Pair every given job with its plan node, keyed the way the plan keys them.

    Ordering is none of this function's business: take it from `flatten_execution_plan`
    where it matters, and look the jobs up by the keys it yields.
    """

    return {job.spec_key: to_rich_job(spec=spec, job=job) for job in jobs}


def flatten_execution_plan(spec: JobSpecV1) -> tuple[FullSpecKey, ...]:
    """
    Lay a plan out in the order its scripts are to be run.

    The hierarchy is the order, so it alone is walked here.

    Only keys come out: whoever needs the scripts themselves has the plan to take them from.
    """

    return tuple(_flatten_level(level=spec.hierarchy, group_levels=()))


def _flatten_level(level: JobHierarchyLevel, group_levels: tuple[LevelSpecKey, ...]) -> Iterator[FullSpecKey]:
    for level_key in level.fields:
        own_levels = (*group_levels, level_key)

        if child_level := level.child_groups.get(level_key):
            yield from _flatten_level(level=child_level, group_levels=own_levels)
            continue

        yield level_keys_to_full_key(own_levels)


def has_bundle_revert_script(spec: JobSpecV1) -> bool:
    return any(
        script_spec.script.type == ScriptType.INTERNAL and script_spec.script.path == "bundle_revert"
        for script_spec in spec.scripts.values()
    )


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
