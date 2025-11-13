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
from functools import wraps
from typing import Callable, Literal, TypeAlias
from uuid import UUID
import uuid

from core.job.dto import LogCreateDTO, TaskPayloadDTO
from core.job.types import ActionInfo, CallingProcess, JobSpec
from core.types import ActionID, ActionProcessID, ActionProcessStepID, ActionTargetDescriptor, CoreObjectDescriptor
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.db.utils import DatabaseError
from django.utils import timezone

from cm.adcm_config.checks import check_attr
from cm.adcm_config.config import (
    check_config_spec,
    get_spec_flat_spec_config_attr_from_prototype_configs,
    process_config_spec,
)
from cm.converters import core_type_to_model
from cm.logger import logger
from cm.models import ProcessStep, ProcessStepInput, PrototypeConfig
from cm.services.action_process import repo_old as repo
from cm.services.action_process.errors import ActionProcessDBError, ActionProcessOperationError, SyncKeyMismatchError
from cm.services.action_process.render_step_old import RenderStepContext, fill_step_spec
from cm.services.action_process.repo_old import get_allowed_ops, get_done_step_inputs_for_process, upsert_step_input
from cm.services.action_process.schema_validation import (
    CompleteProcessPayload,
    Configuration,
    HostComponentMapDelta,
    ProcessOperationType,
    ResetStepPayload,
    SubmitStepPayload,
)
from cm.services.action_process.types_old import (
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
from cm.services.bundle_alt.render import ActionArgs, Environment, render_process
from cm.services.concern.flags import BuiltInFlag, lower_flag
from cm.services.config import ConfigAttrPair, convert_adcm_meta_to_attr, represent_string_as_json_type
from cm.services.job.run import start_task
from cm.services.job.run.repo import JobRepoImpl
from cm.variant import process_variant

SerializedConfigStep: TypeAlias = dict[
    Literal["configuration"], dict[Literal["config_schema", "adcm_meta", "config"], dict | None]
]
SerializedOperationStep: TypeAlias = dict[Literal["ui_options", "task"], dict | None]
OperationPayload: TypeAlias = SubmitStepPayload | CompleteProcessPayload | ResetStepPayload


ConfigProcessor = Callable[[Step, Configuration], ConfigAttrPair]


@dataclass(frozen=True, slots=True)
class OperationContext:
    object: CoreObjectDescriptor
    action: ActionInfo
    config_processor: ConfigProcessor


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
def perform_operation(process_id: ActionProcessID, payload: OperationPayload, context: OperationContext) -> None:
    process = repo.retrieve_process(process_id=process_id)
    _check_sync_key(sync_key=payload.params.process_sync_key, process=process)

    new_process_sync_key = uuid.uuid4()

    match payload.method:
        case ProcessOperationType.SUBMIT:
            submit_step(process=process, payload=payload, context=context, new_process_sync_key=new_process_sync_key)

        case ProcessOperationType.RESET:
            reset_step(process=process, payload=payload, context=context)

        case ProcessOperationType.COMPLETE:
            complete_process(process=process)
            lower_flag(BuiltInFlag.ACTION_PROCESS_RUNNING.value.name, on_objects=[context.object])

    update_process_sync_key(
        process_id=process_id, sync_key=payload.params.process_sync_key, new_sync_key=new_process_sync_key
    )


def submit_step(
    process: ActionProcess, new_process_sync_key: UUID, payload: SubmitStepPayload, context: OperationContext
) -> None:
    _check_step_is_current(process=process, payload=payload)
    _check_no_running_steps(process=process)

    step = repo.retrieve_step(process_id=process.id, step_id=payload.params.step_id)
    match step.type:
        case StepType.CONFIGURATION:
            _operation_submit_config(
                process=process,
                step=step,
                configuration=payload.params.configuration,
                context=context,
            )

        case StepType.OPERATION:
            _operation_submit_job(
                process=process,
                step_id=payload.params.step_id,
                new_process_sync_key=new_process_sync_key,
                parent_object=context.object,
                action=context.action,
            )
        case StepType.MAPPING:
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
    _check_hc_mapping_delta(step, hc_mapping_delta, cluster_id=context.object.id)

    perform_mapping(process.id, step.id, step_input_data)

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


def process_payload_config(step: Step, config: Configuration) -> ConfigAttrPair:
    json_proto_configs = [PrototypeConfig(**cfg) for cfg in step.step_spec if cfg["type"] == "json"]
    config_ = represent_string_as_json_type(prototype_configs=json_proto_configs, value=config.config)
    attr_ = convert_adcm_meta_to_attr(adcm_meta=config.adcm_meta)

    return ConfigAttrPair(config=config_, attr=attr_)


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
    configuration: Configuration,
    *,
    context: OperationContext,
) -> None:
    config_attr_pair = context.config_processor(step, configuration)
    _validate_config(config=config_attr_pair, step=step, context=context)

    step_input_data = StepInputDTO(configuration=config_attr_pair._asdict(), created_at=timezone.now())
    repo.upsert_step_input(step_id=step.id, data=step_input_data)

    revoke_next_steps(process_id=process.id, step_id=step.id)
    complete_step(
        process_id=process.id,
        step_id=step.id,
        action_id=context.action.id,
        object_=context.object,
    )


def _validate_config(config: ConfigAttrPair, step: Step, context: OperationContext) -> None:
    object_orm = core_type_to_model(context.object.type).objects.get(id=context.object.id)
    action_orm = repo.retrieve_action_orm(action_id=context.action.id)
    step_orm = repo.retrieve_step_orm(step_id=step.id)

    prototype_configs = [PrototypeConfig(**config) for config in step.step_spec]
    spec, flat_spec, _, _ = get_spec_flat_spec_config_attr_from_prototype_configs(
        prototype=object_orm.prototype, prototype_configs=prototype_configs
    )

    check_attr(proto=action_orm.prototype, obj=action_orm, attr=config.attr, spec=flat_spec)
    process_variant(obj=object_orm, spec=spec, conf=config.config)
    check_config_spec(
        proto=action_orm.prototype, obj=action_orm, spec=spec, flat_spec=flat_spec, conf=config.config, attr=config.attr
    )
    process_config_spec(obj=step_orm, spec=spec, new_config=config.config)


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


def _check_hc_mapping_delta(step: Step, hc_mapping_delta: HostComponentMapDelta, cluster_id: int) -> None:
    # TO DO: ADCM-7264 for refactoring
    allowed_ops = get_allowed_ops(step, cluster_id)

    for rule in hc_mapping_delta.add or []:
        if rule.component_id not in allowed_ops["add"]:
            raise ActionProcessOperationError(
                f"Add operation not allowed for component_id={rule.component_id}. "
                f"Allowed components for add: {sorted(allowed_ops['add'])}"
            )

    for rule in hc_mapping_delta.remove or []:
        if rule.component_id not in allowed_ops["remove"]:
            raise ActionProcessOperationError(
                f"Remove operation not allowed for component_id={rule.component_id}. "
                f"Allowed components for remove: {sorted(allowed_ops['remove'])}"
            )


@convert_db_errors
@atomic
def perform_mapping(process_id: int, step_id: int, step_input_data: StepInputDTO) -> None:
    mapping_input = step_input_data.mapping
    if not mapping_input or not mapping_input.delta:
        # Nothing to process — just upsert and return
        upsert_step_input(step_id=step_id, data=step_input_data)
        return

    delta = mapping_input.delta.model_dump()
    step_inputs = get_done_step_inputs_for_process(process_id)

    cumulative_add = set()
    cumulative_remove = set()

    for step_input in step_inputs:
        mapping = step_input.mapping or {}
        step_delta = mapping.get("delta")

        if not step_delta:
            continue

        # Apply current step's delta
        for rule in step_delta.get("add", []):
            tup = tuple(sorted(rule.items()))
            cumulative_add.add(tup)
            cumulative_remove.discard(tup)  # Cancel any previous removal

        for rule in step_delta.get("remove", []):
            tup = tuple(sorted(rule.items()))
            if tup in cumulative_add:
                cumulative_add.discard(tup)
            else:
                cumulative_remove.add(tup)

    # Apply the new delta for the current step
    for rule in delta["add"]:
        tup = tuple(sorted(rule.items()))
        cumulative_add.add(tup)
        cumulative_remove.discard(tup)

    for rule in delta["remove"]:
        tup = tuple(sorted(rule.items()))
        if tup in cumulative_add:
            cumulative_add.discard(tup)
        else:
            cumulative_remove.add(tup)

    # Convert sets back to list of dicts
    new_cumulative = {
        "add": [dict(pair) for pair in cumulative_add],
        "remove": [dict(pair) for pair in cumulative_remove],
    }

    new_mapping = {
        "delta": delta,
        "cumulative_delta": new_cumulative,
    }
    step_input_data.mapping = MappingInputDTO(**new_mapping)

    upsert_step_input(step_id=step_id, data=step_input_data)
