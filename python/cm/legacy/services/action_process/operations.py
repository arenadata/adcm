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
from dataclasses import dataclass
from enum import Enum, auto
from functools import wraps
from typing import Literal, Protocol, TypeAlias, TypeVar
from uuid import UUID
import uuid

from core.legacy.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.legacy.cluster.types import ClusterTopology, HostComponentEntry
from core.legacy.job.dto import LogCreateDTO, TaskPayloadDTO
from core.legacy.job.types import ActionInfo, CallingProcess, JobSpec
from core.types import (
    ActionID,
    ActionProcessID,
    ActionProcessStepID,
    ActionTargetDescriptor,
    ComponentID,
    CoreObjectDescriptor,
    HostID,
)
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.db.utils import DatabaseError
from django.utils import timezone
from typing_extensions import Self
import core

from cm.converters import core_type_to_model
from cm.impl.config.repo import build_specification
from cm.legacy.services import mapping
from cm.legacy.services.action_process import repo
from cm.legacy.services.action_process.errors import (
    ActionProcessDBError,
    ActionProcessOperationError,
    ActionProcessPayloadError,
    SyncKeyMismatchError,
)
from cm.legacy.services.action_process.render_step import RenderStepContext, fill_step_spec
from cm.legacy.services.action_process.schema_validation import (
    CompleteProcessPayload,
    Configuration,
    HostComponentMapDelta,
    ProcessOperationType,
    ResetStepPayload,
    SubmitConfigurationStepParams,
    SubmitMappingStepParams,
    SubmitOperationStepParams,
    SubmitStepPayload,
)
from cm.legacy.services.action_process.types import (
    ActionProcess,
    MappingInputDTO,
    ProcessState,
    ProcessStepState,
    ProcessUpdateDTO,
    Step,
    StepInputDTO,
    StepType,
    StepUpdateDTO,
)
from cm.legacy.services.bundle import retrieve_bundle_restrictions
from cm.legacy.services.bundle_alt.render import ActionArgs, Environment, render_process
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.concern.flags import BuiltInFlag, lower_flag
from cm.legacy.services.job.run import start_task
from cm.legacy.services.job.run.repo import JobRepoImpl
from cm.logger import logger
from cm.models import ProcessStep, ProcessStepInput, PrototypeConfig

SerializedConfigStep: TypeAlias = dict[
    Literal["configuration"], dict[Literal["config_schema", "adcm_meta", "config"], dict | None]
]
SerializedOperationStep: TypeAlias = dict[Literal["ui_options", "task"], dict | None]
OperationPayload: TypeAlias = SubmitStepPayload | CompleteProcessPayload | ResetStepPayload
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
    object: CoreObjectDescriptor
    action: ActionInfo
    config_processor: ConfigInputProcessor


def find_current_and_last_completed_steps(
    steps: QuerySet[ProcessStep],
) -> tuple[ActionProcessStepID | None, ActionProcessStepID | None]:
    current = None
    last_completed = None

    for id_, state in steps.values_list("id", "state").order_by("-id"):
        if state in {ProcessStepState.CREATED, ProcessStepState.RUNNING}:
            current = id_

        if last_completed is None and state == ProcessStepState.COMPLETED:
            last_completed = id_

        if current and last_completed:
            break

    return current, last_completed


def initiate_process(object_: CoreObjectDescriptor, action: ActionInfo) -> ActionProcessID:
    object_orm = core_type_to_model(object_.type).objects.get(id=object_.id)
    bundle_root = repo.get_bundle_root_from_prototype(prototype_id=object_orm.prototype_id)

    environment = Environment(bundle_root=bundle_root)
    action_args = ActionArgs(
        action=repo.retrieve_action_orm(action_id=action.id),
        cluster_relative_object=object_orm,
        action_process=None,
    )
    stages = render_process(template=action.wizard_template, environment=environment, context_args=action_args)
    db_stages = repo.convert_stages_to_db_format(stages=stages)
    process = repo.create_process(object_=object_, action_id=action.id, stages=db_stages)

    # Works with bulk_create only if the Step model’s primary key is an AutoField, ignore_conflicts=False and
    # db is PostgreSQL, MariaDB, or SQLite 3.35+
    # https://docs.djangoproject.com/en/5.1/ref/models/querysets/#bulk-create
    steps = repo.create_steps(process_id=process.id, stages=stages)
    current_step_id = steps[0].id

    repo.update_process(
        process_id=process.id,
        data=ProcessUpdateDTO(current_step=current_step_id, flow_spec=db_stages),
    )

    context = RenderStepContext(process_id=process.id, action_id=action.id, object=object_)
    fill_step_spec(step_id=current_step_id, context=context)

    return process.id


def complete_process(process: ActionProcess) -> None:
    _check_all_steps_completed(process=process)
    repo.set_process_status(process=process, state=ProcessState.COMPLETED)


def complete_step(
    process_id: ActionProcessID,
    step_id: ActionProcessStepID,
    action_id: ActionID,
    object_: CoreObjectDescriptor,
) -> None:
    """Set step's status to `completed`, process's current_step and last_completed_step; render next step"""

    repo.update_step(step_id=step_id, data=StepUpdateDTO(state=ProcessStepState.COMPLETED))

    current_id, last_completed_id = find_current_and_last_completed_steps(
        steps=ProcessStep.objects.filter(process_id=process_id)
    )
    repo.update_process(
        process_id=process_id,
        data=ProcessUpdateDTO(current_step=current_id, last_completed_step=last_completed_id),
    )
    if current_id:
        context = RenderStepContext(process_id=process_id, action_id=action_id, object=object_)
        fill_step_spec(step_id=current_id, context=context)


def complete_operation_step(
    process_id: ActionProcessID,
    process_sync_key: UUID,
    step_id: ActionProcessStepID,
    action_id: ActionID,
    object_: CoreObjectDescriptor,
    is_operation_success: bool,
) -> None:
    update_process_sync_key(process_id=process_id, sync_key=process_sync_key, new_sync_key=uuid.uuid4())

    if not is_operation_success:
        repo.update_step(step_id=step_id, data=StepUpdateDTO(state=ProcessStepState.CREATED))
        # We are not deleting the ProcessStepInput, as it is forbidden to submit a complete step,
        # and we expect that the user will have to reset this step or previous ones,
        # which will entail deleting the current ProcessStepInput.
        return

    complete_step(process_id=process_id, step_id=step_id, action_id=action_id, object_=object_)


def revoke_next_steps(process_id: ActionProcessID, step_id: ActionProcessStepID) -> set[int]:
    """
    Revokes all steps after the given step_id.
    """
    qs = retrieve_next_steps_qs(process_id, step_id)
    return _repo_revoke_steps(qs)


def revoke_starting_with_step(process_id: ActionProcessID, step_id: ActionProcessStepID) -> set[int]:
    """
    Revokes the given step_id and all following steps.
    """
    qs = retrieve_steps_starting_with_qs(process_id, step_id)
    return _repo_revoke_steps(qs)


def retrieve_next_steps_qs(process_id: ActionProcessID, step_id: ActionProcessStepID) -> QuerySet:
    """
    Returns a queryset of steps after the given step_id in the same process.
    """
    return ProcessStep.objects.filter(process_id=process_id, id__gt=step_id).order_by("id")


def retrieve_steps_starting_with_qs(process_id: ActionProcessID, step_id: ActionProcessStepID) -> QuerySet:
    """
    Returns a queryset of steps starting from (and including) step_id in the same process.
    """
    return ProcessStep.objects.filter(process_id=process_id, id__gte=step_id)


def update_process_sync_key(process_id: ActionProcessID, sync_key: UUID, new_sync_key: UUID) -> None:
    """
    Find a process specified by process_id and sync_key and updates it's sync_key value
    """
    if not repo.update_process_sync_key(process_id=process_id, sync_key=sync_key, new_sync_key=new_sync_key):
        raise SyncKeyMismatchError(f"There is no #{process_id} process with sync_key {sync_key}")


def _repo_revoke_steps(steps_qs: QuerySet) -> set[int]:
    """
    Deletes inputs and clears specs for the given steps.
    Operates directly on the queryset to avoid loading IDs unnecessarily.
    Returns the set of step IDs revoked.
    """
    step_ids = set(steps_qs.values_list("id", flat=True))
    ProcessStepInput.objects.filter(step_id__in=step_ids).delete()
    ProcessStep.objects.filter(id__in=step_ids).update(state=ProcessStepState.CREATED, step_spec=None)
    return step_ids


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


@convert_db_errors
@atomic
def perform_operation(
    process_id: ActionProcessID,
    payload: OperationPayload,
    context: OperationContext,
    config_service: core.config.ConfigService,
) -> None:
    process = repo.retrieve_process(process_id=process_id)
    _check_sync_key(sync_key=payload.params.process_sync_key, process=process)

    new_process_sync_key = uuid.uuid4()

    match payload.method:
        case ProcessOperationType.SUBMIT:
            submit_step(
                process=process,
                payload=payload,
                context=context,
                new_process_sync_key=new_process_sync_key,
                config_service=config_service,
            )

        case ProcessOperationType.RESET:
            reset_step(process=process, payload=payload, context=context)

        case ProcessOperationType.COMPLETE:
            complete_process(process=process)
            lower_flag(BuiltInFlag.ACTION_PROCESS_RUNNING.value.name, on_objects=[context.object])

    update_process_sync_key(
        process_id=process_id, sync_key=payload.params.process_sync_key, new_sync_key=new_process_sync_key
    )


def submit_step(
    process: ActionProcess,
    new_process_sync_key: UUID,
    payload: SubmitStepPayload,
    context: OperationContext,
    config_service: core.config.ConfigService,
) -> None:
    _check_step_is_current(process=process, payload=payload)
    _check_no_running_steps(process=process)

    step = repo.retrieve_step(process_id=process.id, step_id=payload.params.step_id)
    msg_wrong_payload = f"Wrong params for {step.type} step"

    match step.type:
        case StepType.CONFIGURATION:
            if not isinstance(payload.params, SubmitConfigurationStepParams):
                raise ActionProcessPayloadError(msg_wrong_payload)

            _operation_submit_config(
                process=process,
                step=step,
                input_config=payload.params.configuration,
                context=context,
                config_service=config_service,
            )

        case StepType.OPERATION:
            if not isinstance(payload.params, SubmitOperationStepParams):
                raise ActionProcessPayloadError(msg_wrong_payload)

            _operation_submit_job(
                process=process,
                step_id=payload.params.step_id,
                new_process_sync_key=new_process_sync_key,
                parent_object=context.object,
                action=context.action,
            )
        case StepType.MAPPING:
            if not isinstance(payload.params, SubmitMappingStepParams):
                raise ActionProcessPayloadError(msg_wrong_payload)

            _operation_submit_mapping(
                process=process,
                step=step,
                hc_mapping_delta=payload.params.host_component_map_delta,
                context=context,
            )


def _operation_submit_mapping(
    process: ActionProcess,
    step: Step,
    hc_mapping_delta: HostComponentMapDelta,
    *,
    context: OperationContext,
) -> None:
    step_input_data = StepInputDTO(
        configuration=None, job_id=None, mapping=MappingInputDTO(delta=hc_mapping_delta), created_at=timezone.now()
    )
    _check_hc_mapping_delta(step=step, hc_mapping_delta=hc_mapping_delta, object_=context.object)

    perform_mapping(process_id=process.id, step_id=step.id, step_input_data=step_input_data)

    revoke_next_steps(process_id=process.id, step_id=step.id)
    complete_step(
        process_id=process.id,
        step_id=step.id,
        action_id=context.action.id,
        object_=context.object,
    )


def reset_step(process: ActionProcess, payload: ResetStepPayload, context: OperationContext) -> None:
    _check_no_running_steps(process=process)

    revoke_starting_with_step(process_id=process.id, step_id=payload.params.step_id)
    current_id, last_completed_id = find_current_and_last_completed_steps(
        steps=ProcessStep.objects.filter(process_id=process.id)
    )

    repo.update_process(
        process_id=process.id,
        data=ProcessUpdateDTO(current_step=current_id, last_completed_step=last_completed_id),
    )
    if current_id:
        render_context = RenderStepContext(process_id=process.id, action_id=context.action.id, object=context.object)
        fill_step_spec(step_id=current_id, context=render_context)


def _operation_submit_job(
    process: ActionProcess,
    step_id: int,
    new_process_sync_key: UUID,
    *,
    parent_object: CoreObjectDescriptor,
    action: ActionInfo,
) -> None:
    job_repo = JobRepoImpl

    step = repo.retrieve_step(process_id=process.id, step_id=step_id)
    target = ActionTargetDescriptor(id=parent_object.id, type=parent_object.type)
    payload = TaskPayloadDTO(
        process=CallingProcess(id=process.id, sync_key=new_process_sync_key, step_id=process.current_step_id)
    )

    task = job_repo.create_task(target=target, owner=parent_object, action=action, payload=payload)
    job_repo.create_jobs(task_id=task.id, jobs=[JobSpec(**job) for job in step.step_spec])

    logs = []
    for job in job_repo.get_task_jobs(task_id=task.id):
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stdout", format="txt"))
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stderr", format="txt"))

    if logs:
        job_repo.create_logs(logs)

    task_orm = repo.retrieve_task_orm(task_id=task.id)

    step_input_data = StepInputDTO(job_id=task_orm.id, created_at=timezone.now())
    repo.upsert_step_input(step_id=step_id, data=step_input_data)

    revoke_next_steps(process_id=process.id, step_id=step_id)
    repo.update_step(step_id=step_id, data=StepUpdateDTO(state=ProcessStepState.RUNNING))

    # todo write pid to task (executor)
    start_task(task=task_orm)


def _operation_submit_config(
    process: ActionProcess,
    step: Step,
    input_config: Configuration,
    *,
    context: OperationContext,
    config_service: core.config.ConfigService,
) -> None:
    prototype_conifgs = tuple(PrototypeConfig(**cfg) for cfg in step.step_spec)
    specification = build_specification(records=prototype_conifgs, group_customization_flag=False)

    try:
        owner_config = config_service.retrieve_current_configuration(owner=context.object)
    except core.config.ObjectWithoutConfigError:
        owner_config = None

    configuration = context.config_processor(input_config, specification)
    step_configuration = config_service.prepare_action_configuration(
        configuration=configuration,
        specification=specification,
        owner=context.object,
        owner_configuration=owner_config,
    )
    prefix = core.config.files.build_action_process_step_prefix(process_id=process.id, step_id=step.id)
    config_service.prepare_file_parameter_values_on_fs(
        configuration=step_configuration, specification=specification, owner_prefix=prefix
    )

    step_input_data = StepInputDTO(configuration=step_configuration, created_at=timezone.now())
    repo.upsert_step_input(step_id=step.id, data=step_input_data)

    revoke_next_steps(process_id=process.id, step_id=step.id)
    complete_step(process_id=process.id, step_id=step.id, action_id=context.action.id, object_=context.object)


def _check_step_is_current(process: ActionProcess, payload: SubmitStepPayload) -> None:
    current_step_id, _ = find_current_and_last_completed_steps(steps=ProcessStep.objects.filter(process_id=process.id))
    if payload.params.step_id != current_step_id:
        raise ActionProcessOperationError("Only current step can be submitted")


def _check_sync_key(sync_key: UUID, process: ActionProcess) -> None:
    if process.sync_key != sync_key:
        raise SyncKeyMismatchError(f"Can't find Process #{process.id} ({str(sync_key)})")


def _check_no_running_steps(process: ActionProcess) -> None:
    if repo.retrieve_running_step_ids(process_id=process.id):
        raise ActionProcessOperationError("There is a running step")


def _check_all_steps_completed(process: ActionProcess) -> None:
    for step in repo.retrieve_steps(process_id=process.id):
        if step.state != ProcessStepState.COMPLETED:
            raise ActionProcessOperationError("All steps must be completed")


def _check_hc_mapping_delta(step: Step, hc_mapping_delta: HostComponentMapDelta, object_: CoreObjectDescriptor) -> None:
    cluster_id, bundle_id = repo.retrieve_related_cluster_id_and_cluster_bundle_id(object_=object_)
    topology = retrieve_cluster_topology(cluster_id=cluster_id)

    if existence_violations := _find_mapping_delta_objects_existence_violations(
        delta=hc_mapping_delta, topology=topology
    ):
        existence_violations[0].raise_error()

    # if there is previous mapping step with cumulative_delta: "apply" cumulative_delta to topology
    if previous_mapping_input := repo.retrieve_previous_mapping_step_input_with_cumulative_delta(
        process_id=step.process_id, step_id=step.id
    ):
        mapping_considering_cumulative_delta = _get_new_flat_mapping_from_delta_and_topology(
            delta=previous_mapping_input.mapping.cumulative_delta, topology=topology
        )
        topology = create_topology_with_new_mapping(topology=topology, new_mapping=mapping_considering_cumulative_delta)

    # TODO: unite with cm.legacy.services.job._utils.check_delta_is_allowed
    mapping_rules = _prepare_mapping_rules(step=step, topology=topology)
    if distribution_violations := _find_hc_operation_distribution_violations(
        delta=hc_mapping_delta, rules=mapping_rules, topology=topology
    ):
        distribution_violations[0].raise_error()

    new_mapping = _get_new_flat_mapping_from_delta_and_topology(delta=hc_mapping_delta, topology=topology)
    new_topology = create_topology_with_new_mapping(topology=topology, new_mapping=new_mapping)
    host_difference = find_hosts_difference(new_topology=new_topology, old_topology=topology)
    bundle_restrictions = retrieve_bundle_restrictions(bundle_id=bundle_id)

    mapping.check_all(
        bundle_restrictions=bundle_restrictions,
        new_topology=new_topology,
        host_difference=host_difference,
    )


def _get_new_flat_mapping_from_delta_and_topology(
    delta: HostComponentMapDelta, topology: ClusterTopology
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


def _prepare_mapping_rules(step: Step, topology: ClusterTopology) -> MappingRules:
    """Filter mapping rules from step_spec by existing in topology components"""

    comp_full_name_id_map = topology.component_full_name_id_mapping
    rules = defaultdict(set)

    for spec in step.step_spec:
        key = core.types.ComponentNameKey(service=spec["service"], component=spec["component"])
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


def _find_mapping_delta_objects_existence_violations(
    delta: HostComponentMapDelta, topology: ClusterTopology
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


def _find_hc_operation_distribution_violations(
    delta: HostComponentMapDelta, rules: MappingRules, topology: ClusterTopology
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


@convert_db_errors
def perform_mapping(process_id: int, step_id: int, step_input_data: StepInputDTO) -> None:
    mapping_input = step_input_data.mapping
    if not mapping_input or not mapping_input.delta:
        # Nothing to process — just upsert and return
        repo.upsert_step_input(step_id=step_id, data=step_input_data)
        return

    cumulative_delta = {"add": set(), "remove": set()}
    input_ = repo.retrieve_previous_mapping_step_input_with_cumulative_delta(process_id=process_id, step_id=step_id)
    if input_ and input_.mapping.cumulative_delta:
        cumulative_delta = {
            op: {tuple(sorted(hc.items())) for hc in hc_list}
            for op, hc_list in input_.mapping.cumulative_delta.model_dump().items()
        }

    delta = mapping_input.delta.model_dump()

    # Apply the new delta for the current step
    for rule in delta["add"]:
        tup = tuple(sorted(rule.items()))
        cumulative_delta["add"].add(tup)
        cumulative_delta["remove"].discard(tup)

    for rule in delta["remove"]:
        tup = tuple(sorted(rule.items()))
        if tup in cumulative_delta["add"]:
            cumulative_delta["add"].discard(tup)
        else:
            cumulative_delta["remove"].add(tup)

    # Convert sets back to list of dicts
    cumulative_delta = {op: [dict(hc) for hc in hc_set] for op, hc_set in cumulative_delta.items()}
    step_input_data.mapping = MappingInputDTO(delta=delta, cumulative_delta=cumulative_delta)

    repo.upsert_step_input(step_id=step_id, data=step_input_data)
