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

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto
from functools import wraps
from typing import Literal, Protocol, TypeAlias, TypeVar

from core.action import wizard
from core.legacy.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.legacy.cluster.types import ClusterTopology, HostComponentEntry
from core.types import (
    ActionProcessStepID,
    ComponentID,
    ComponentNameKey,
    CoreObjectDescriptor,
    HostID,
)
from django.db.utils import DatabaseError
from typing_extensions import Self
import core

from cm.legacy.services import mapping
from cm.legacy.services.action_process.errors import (
    ActionProcessDBError,
    ActionProcessOperationError,
)
from cm.legacy.services.action_process.schema_validation import (
    CompleteProcessPayload,
    ResetStepPayload,
    SkipStepPayload,
    SubmitStepPayload,
)
from cm.legacy.services.action_process.types import ProcessContext
from cm.legacy.services.bundle import retrieve_bundle_restrictions
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.logger import logger

SerializedConfigStep: TypeAlias = dict[
    Literal["configuration"], dict[Literal["config_schema", "adcm_meta", "config"], dict | None]
]

SerializedOperationStep: TypeAlias = dict[Literal["ui_options", "task", "required"], dict | None]
OperationPayload: TypeAlias = SubmitStepPayload | CompleteProcessPayload | ResetStepPayload | SkipStepPayload
MappingRules: TypeAlias = dict[Literal["add", "remove"], set[ComponentID]]


T = TypeVar("T", contravariant=True)


class HCViolationType(Enum):
    HOSTS_ABSENT = auto()
    COMPONENTS_ABSENT = auto()
    ADD_RULE = auto()
    ADD_SANITY = auto()
    REMOVE_RULE = auto()
    REMOVE_SANITY = auto()


class HCErrorFormatter(Protocol):
    def __call__(
        self,
        ids: set[HostID | ComponentID],
        type_: HCViolationType,
        topology: ClusterTopology,
        hc_rules: MappingRules | None,
    ) -> str:
        ...


@dataclass(slots=True, frozen=True)
class HCViolation:
    ids: set[HostID | ComponentID]
    type_: HCViolationType
    topology: ClusterTopology
    formatter: HCErrorFormatter
    hc_rules: MappingRules | None = None
    err_cls: type[Exception] = ActionProcessOperationError

    def raise_error(self: Self) -> None:
        raise self.err_cls(
            self.formatter(ids=self.ids, type_=self.type_, topology=self.topology, hc_rules=self.hc_rules)
        )


class ConfigInputProcessor(Protocol[T]):
    def __call__(self, configuration: T, specification: core.config.spec.FullSpec, /) -> core.config.Configuration:
        ...


@dataclass(frozen=True, slots=True)
class OperationContext:
    process_context: ProcessContext
    config_processor: ConfigInputProcessor


def find_current_and_last_completed_steps(
    steps: Iterable[wizard.Step],
) -> tuple[ActionProcessStepID | None, ActionProcessStepID | None]:
    current = None
    last_completed = None

    for step in sorted(steps, key=lambda s: s.id, reverse=True):
        if step.state in {wizard.ProcessStepState.CREATED, wizard.ProcessStepState.RUNNING}:
            current = step.id

        if last_completed is None and step.state == wizard.ProcessStepState.COMPLETED:
            last_completed = step.id

        if current and last_completed:
            break

    return current, last_completed


def convert_db_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DatabaseError as e:
            logger.exception("Database error during performing process' operation")

            msg = "Can't update action process. Most likely due to parallel modification"
            raise ActionProcessDBError(msg) from e

    return wrapper


def check_hc_mapping_delta(
    step: wizard.Step,
    hc_mapping_delta: wizard.HostComponentMapDelta,
    object_: CoreObjectDescriptor,
    wizard_repo: core.action.wizard.WizardRepoI,
) -> None:
    cluster_id, bundle_id = wizard_repo.retrieve_related_cluster_id_and_cluster_bundle_id(object_=object_)
    topology = retrieve_cluster_topology(cluster_id=cluster_id)

    if existence_violations := find_mapping_delta_objects_existence_violations(
        delta=hc_mapping_delta, topology=topology
    ):
        existence_violations[0].raise_error()

    # if there is previous mapping step with cumulative_delta: "apply" cumulative_delta to topology
    if previous_mapping_input := wizard_repo.retrieve_previous_mapping_step_input_with_cumulative_delta(
        process_id=step.process_id, step_id=step.id
    ):
        mapping_considering_cumulative_delta = get_new_flat_mapping_from_delta_and_topology(
            delta=previous_mapping_input.mapping.cumulative_delta, topology=topology
        )
        topology = create_topology_with_new_mapping(topology=topology, new_mapping=mapping_considering_cumulative_delta)

    # TODO: unite with cm.legacy.services.job._utils.check_delta_is_allowed
    mapping_rules = prepare_mapping_rules(step=step, topology=topology)
    if distribution_violations := find_hc_operation_distribution_violations(
        delta=hc_mapping_delta, rules=mapping_rules, topology=topology
    ):
        distribution_violations[0].raise_error()

    new_mapping = get_new_flat_mapping_from_delta_and_topology(delta=hc_mapping_delta, topology=topology)
    new_topology = create_topology_with_new_mapping(topology=topology, new_mapping=new_mapping)
    host_difference = find_hosts_difference(new_topology=new_topology, old_topology=topology)
    bundle_restrictions = retrieve_bundle_restrictions(bundle_id=bundle_id)

    mapping.check_for_main_mapping(
        bundle_restrictions=bundle_restrictions,
        new_topology=new_topology,
        host_difference=host_difference,
    )


def get_new_flat_mapping_from_delta_and_topology(
    delta: wizard.HostComponentMapDelta, topology: ClusterTopology
) -> list[HostComponentEntry]:
    flat_hc: set[tuple[HostID, ComponentID]] = {
        (host_id, component_id)
        for component_id, host_ids in topology.component_host_id_map.items()
        for host_id in host_ids
    }

    for hc_entry in delta.add:
        flat_hc.add((hc_entry.host_id, hc_entry.component_id))

    for hc_entry in delta.remove:
        flat_hc.discard((hc_entry.host_id, hc_entry.component_id))

    return [HostComponentEntry(host_id=host_id, component_id=component_id) for host_id, component_id in flat_hc]


def prepare_mapping_rules(step: wizard.Step, topology: ClusterTopology) -> MappingRules:
    """Filter mapping rules from step_spec by existing in topology components"""

    comp_full_name_id_map = topology.component_full_name_id_mapping
    rules = defaultdict(set)

    for spec in step.step_spec:
        key = ComponentNameKey(service=spec["service"], component=spec["component"])
        if component_id := comp_full_name_id_map.get(key):
            rules[spec["operation"]].add(component_id)

    return rules


def _format_hc_existence_error(
    ids: set[HostID | ComponentID],
    type_: HCViolationType,
    topology: ClusterTopology,
    hc_rules: MappingRules | None,
) -> str:
    _ = hc_rules

    match type_:
        case HCViolationType.HOSTS_ABSENT:
            obj_cls_repr = "Host"
        case HCViolationType.COMPONENTS_ABSENT:
            obj_cls_repr = "Component"
        case _:
            raise NotImplementedError(f"Unexpected violation type for existence violation: {type_}")

    ids_repr = ", ".join(f"#{id_}" for id_ in sorted(ids))

    return f"{obj_cls_repr}(s) {ids_repr} not found in cluster #{topology.cluster_id}"


def find_mapping_delta_objects_existence_violations(
    delta: wizard.HostComponentMapDelta, topology: ClusterTopology
) -> list[HCViolation]:
    violations = []

    host_ids, component_ids = set(), set()
    for hc_pair in delta.add + delta.remove:
        host_ids.add(hc_pair.host_id)
        component_ids.add(hc_pair.component_id)

    if host_errors := host_ids.difference(set(topology.hosts)):
        violations.append(
            HCViolation(
                ids=host_errors,
                type_=HCViolationType.HOSTS_ABSENT,
                topology=topology,
                formatter=_format_hc_existence_error,
            )
        )

    if component_errors := component_ids.difference(set(topology.component_ids)):
        violations.append(
            HCViolation(
                ids=component_errors,
                type_=HCViolationType.COMPONENTS_ABSENT,
                topology=topology,
                formatter=_format_hc_existence_error,
            )
        )

    return violations


def _format_hc_distribution_error(
    ids: set[HostID | ComponentID],
    type_: HCViolationType,
    topology: ClusterTopology,
    hc_rules: MappingRules | None,
) -> str:
    err_template = "{operation} operation is not allowed for {component_names}. {detail}."
    comp_id_full_name_map = {v: k for k, v in topology.component_full_name_id_mapping.items()}
    names = sorted(comp_id_full_name_map[id_].full_name for id_ in ids)
    names_repr = ", ".join(f'"{name}"' for name in names)

    match type_:
        case HCViolationType.ADD_RULE:
            operation = "Add"
            names = sorted(comp_id_full_name_map[id_].full_name for id_ in hc_rules.get("add", ()))
            allowed_for_add = ", ".join(f'"{name}"' for name in names) or "none"
            detail = f"Allowed components for add: {allowed_for_add}"
        case HCViolationType.ADD_SANITY:
            operation = "Add"
            detail = "Already mapped"
        case HCViolationType.REMOVE_RULE:
            operation = "Remove"
            names = sorted(comp_id_full_name_map[id_].full_name for id_ in hc_rules.get("remove", ()))
            allowed_for_remove = ", ".join(f'"{name}"' for name in names) or "none"
            detail = f"Allowed components for remove: {allowed_for_remove}"
        case HCViolationType.REMOVE_SANITY:
            operation = "Remove"
            detail = "Not mapped"
        case _:
            raise NotImplementedError(f"Unexpected violation type for distribution violation: {type_}")

    return err_template.format(operation=operation, component_names=names_repr, detail=detail)


def find_hc_operation_distribution_violations(
    delta: wizard.HostComponentMapDelta, rules: MappingRules, topology: ClusterTopology
) -> list[HCViolation]:
    comp_id_host_ids_map = topology.component_host_id_map
    violations: dict[HCViolationType, set[ComponentID]] = defaultdict(set)

    for hc_pair in delta.add or []:
        if hc_pair.component_id not in rules["add"]:
            violations[HCViolationType.ADD_RULE].add(hc_pair.component_id)

        if hc_pair.host_id in comp_id_host_ids_map[hc_pair.component_id]:
            violations[HCViolationType.ADD_SANITY].add(hc_pair.component_id)

    for hc_pair in delta.remove or []:
        if hc_pair.component_id not in rules["remove"]:
            violations[HCViolationType.REMOVE_RULE].add(hc_pair.component_id)

        if hc_pair.host_id not in comp_id_host_ids_map[hc_pair.component_id]:
            violations[HCViolationType.REMOVE_SANITY].add(hc_pair.component_id)

    return [
        HCViolation(
            ids=ids, type_=violation_type, topology=topology, formatter=_format_hc_distribution_error, hc_rules=rules
        )
        for violation_type, ids in violations.items()
    ]
