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
from typing import Callable, Literal, Optional, TypeAlias
from uuid import UUID, uuid4
import logging

from core.bundle_alt.process import ScriptsConversionContext, parse_scripts
from core.job.dto import LogCreateDTO, TaskPayloadDTO
from core.job.types import ActionInfo
from core.templates import RendererEnv
from core.types import ActionID, ActionProcessID, ActionProcessStepID, ActionTargetDescriptor, CoreObjectDescriptor
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.utils import timezone

from cm.converters import core_type_to_model
from cm.models import ProcessStep, ProcessStepInput
from cm.services.concern.flags import BuiltInFlag, lower_flag
from cm.services.config import ConfigAttrPair
from cm.services.job.run import start_task
from cm.services.job.run.repo import JobRepoImpl
from cm.services.wizard import repo, stage
from cm.services.wizard.errors import SyncKeyMismatchError, WizardOperationError
from cm.services.wizard.render_step import RenderStepContext, render_step, render_template
from cm.services.wizard.schema_validation import (
    CompleteStepPayload,
    Configuration,
    ProcessOperationType,
    ResetStepPayload,
    SubmitStepPayload,
)
from cm.services.wizard.types import (
    ActionProcess,
    ProcessState,
    ProcessStepState,
    ProcessUpdateDTO,
    StepType,
    StepUpdateDTO,
)

SerializedConfigStep: TypeAlias = dict[
    Literal["configuration"], dict[Literal["config_schema", "adcm_meta", "config"], dict | None]
]
SerializedOperationStep: TypeAlias = dict[Literal["ui_options", "task"], dict | None]
OperationPayload: TypeAlias = SubmitStepPayload | CompleteStepPayload | ResetStepPayload


@dataclass(frozen=True, slots=True)
class OperationContext:
    object: CoreObjectDescriptor
    action: ActionInfo
    config_processor: Optional[Callable] = None  # TODO


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
    environment = RendererEnv(
        discovery_root=repo.get_bundle_root_from_prototype(prototype_id=action.owner_prototype.id)
    )
    stages_raw = render_template(
        template=action.wizard_template, environment=environment, action_id=action.id, object_=object_
    )
    stages = stage.convert_stages(stages_raw=stages_raw)

    process = repo.create_process(object_=object_, action_id=action.id, stages=stages)
    repo.create_steps(process_id=process.id, stages=stages)  # TODO: validate stages

    current_id, _ = find_current_and_last_completed_steps(steps=ProcessStep.objects.filter(process_id=process.id))
    repo.update_process(
        process_id=process.id, sync_key=process.sync_key, data=ProcessUpdateDTO(current_step=current_id)
    )

    context = RenderStepContext(process_id=process.id, action_id=action.id, object=object_)
    render_step(step_id=current_id, context=context)

    return process.id


def complete_process(process: ActionProcess) -> None:
    _check_all_steps_completed(process=process)
    repo.set_process_status(process=process, state=ProcessState.COMPLETED)


def complete_step(
    process_id: ActionProcessID,
    step_id: ActionProcessStepID,
    sync_key: UUID,
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
        sync_key=sync_key,
        data=ProcessUpdateDTO(current_step=current_id, last_completed_step=last_completed_id),
    )
    if current_id:
        context = RenderStepContext(process_id=process_id, action_id=action_id, object=object_)
        render_step(step_id=current_id, context=context)


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


def update_process_sync_key(process_id: ActionProcessID, sync_key: UUID) -> None:
    if not repo.update_process(process_id=process_id, sync_key=sync_key, data=ProcessUpdateDTO(sync_key=uuid4())):
        raise SyncKeyMismatchError(f"Can't find Process #{process_id} ({str(sync_key)})")


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


@atomic
def perform_operation(process_id: ActionProcessID, payload: OperationPayload, context: OperationContext) -> None:
    process = repo.retrieve_process(process_id=process_id)
    _check_sync_key(sync_key=payload.params.process_sync_key, process=process)

    match payload.method:
        case ProcessOperationType.SUBMIT:
            submit_step(process=process, payload=payload, context=context)

        case ProcessOperationType.RESET:
            reset_step(process=process, payload=payload, context=context)

        case ProcessOperationType.COMPLETE:
            complete_process(process=process)
            lower_flag(BuiltInFlag.WIZARD_PROCESS_RUNNING.value.name, on_objects=[context.object])

    update_process_sync_key(process_id=process_id, sync_key=payload.params.process_sync_key)


def submit_step(process: ActionProcess, payload: SubmitStepPayload, context: OperationContext) -> None:
    _check_step_is_current(process=process, payload=payload)
    _check_no_running_steps(process=process)

    step = repo.retrieve_step(process_id=process.id, step_id=payload.params.step_id)
    match step.type:
        case StepType.CONFIGURATION:
            config: ConfigAttrPair = _prepare_step_config_input(
                process_id=process.id, step_id=payload.params.step_id, config=payload.params.configuration
            )
            _operation_submit_config(
                process=process,
                step_id=payload.params.step_id,
                configuration=config,
                sync_key=payload.params.process_sync_key,
                object_=context.object,
                action=context.action,
            )

        case StepType.OPERATION:
            _operation_submit_job(
                process=process, step_id=payload.params.step_id, parent_object=context.object, action=context.action
            )


def reset_step(process: ActionProcess, payload: ResetStepPayload, context: OperationContext) -> None:
    _check_no_running_steps(process=process)

    revoke_starting_with_step(process_id=process.id, step_id=payload.params.step_id)
    current_id, last_completed_id = find_current_and_last_completed_steps(
        steps=ProcessStep.objects.filter(process_id=process.id)
    )

    repo.update_process(
        process_id=process.id,
        sync_key=payload.params.process_sync_key,
        data=ProcessUpdateDTO(current_step=current_id, last_completed_step=last_completed_id),
    )
    if current_id:
        render_context = RenderStepContext(process_id=process.id, action_id=context.action.id, object=context.object)
        render_step(step_id=current_id, context=render_context)


def _prepare_step_config_input(  # TODO: https://tracker.yandex.ru/ADCM-6942
    process_id: int,  # noqa: ARG001
    step_id: int,  # noqa: ARG001
    config: Configuration,
) -> ConfigAttrPair:
    from api_v2.generic.config.utils import convert_adcm_meta_to_attr
    # todo make it work
    # step = repo.retrieve_step(process_id=process_id, step_id=step_id)
    # config = represent_string_as_json_type()

    # todo do something with this bs
    attr = convert_adcm_meta_to_attr(config.adcm_meta)

    return ConfigAttrPair(config=config.config, attr=attr)


def _operation_submit_job(
    process: ActionProcess,
    step_id: int,
    *,
    parent_object: CoreObjectDescriptor,  # target == owner,Cluster,Service,Component,Provider,Host/ActionHostGroup???
    action: ActionInfo,
) -> None:
    job_repo = JobRepoImpl
    owner = parent_object  # target == owner

    step = repo.retrieve_step(process_id=process.id, step_id=step_id)
    step_raw_spec = repo.find_raw_step_spec(step=step, process_flow_spec=process.flow_spec)

    prototype_id = core_type_to_model(parent_object.type).objects.get(id=parent_object.id).prototype_id
    bundle_root_path = repo.get_bundle_root_from_prototype(prototype_id=prototype_id)
    template_path = bundle_root_path / step_raw_spec.template.file.path

    target = ActionTargetDescriptor(id=owner.id, type=owner.type)
    payload = TaskPayloadDTO()

    task = job_repo.create_task(target=target, owner=owner, action=action, payload=payload)

    allow_to_terminate = repo.retrieve_action_orm(action_id=action.id).allow_to_terminate
    context = ScriptsConversionContext(
        source_dir=template_path.parent,
        action_allow_to_terminate=allow_to_terminate,
    )
    jobs = list(parse_scripts(data=step.step_spec, context=context))
    job_repo.create_jobs(task_id=task.id, jobs=jobs)

    logs = []
    for job in job_repo.get_task_jobs(task_id=task.id):
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stdout", format="txt"))
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stderr", format="txt"))

    if logs:
        job_repo.create_logs(logs)

    task_orm = repo.retrieve_task_orm(task_id=task.id)
    logging.getLogger("adcm").error(f"{task_orm.action=}")

    data = {"step_id": step_id, "configuration": None, "job_id": task_orm.id, "created_at": timezone.now()}
    step_input_qs = ProcessStepInput.objects.filter(step_id=step_id)

    if not step_input_qs.exists():
        ProcessStepInput.objects.create(**data)
    else:
        step_input_qs.update(**data)

    revoke_next_steps(process_id=process.id, step_id=step_id)
    repo.update_step(step_id=step_id, data=StepUpdateDTO(state=ProcessStepState.RUNNING))

    # todo write pid to task (executor)
    start_task(task=task_orm)


def _operation_submit_config(
    process: ActionProcess,
    step_id: ActionProcessStepID,
    configuration: ConfigAttrPair,
    *,
    sync_key: UUID,
    object_: CoreObjectDescriptor,
    action: ActionInfo,
) -> None:
    data = {"step_id": step_id, "configuration": configuration._asdict(), "job": None, "created_at": timezone.now()}
    step_input_qs = ProcessStepInput.objects.filter(step_id=step_id)

    if not step_input_qs.exists():
        ProcessStepInput.objects.create(**data)
    else:
        step_input_qs.update(**data)

    revoke_next_steps(process_id=process.id, step_id=step_id)

    complete_step(
        process_id=process.id,
        step_id=step_id,
        sync_key=sync_key,
        action_id=action.id,
        object_=object_,
    )


def _check_step_is_current(process: ActionProcess, payload: SubmitStepPayload) -> None:
    current_step_id, _ = find_current_and_last_completed_steps(steps=ProcessStep.objects.filter(process_id=process.id))
    if payload.params.step_id != current_step_id:
        raise WizardOperationError("Only current step can be submitted.")


def _check_sync_key(sync_key: UUID, process: ActionProcess) -> None:
    if process.sync_key != sync_key:
        raise SyncKeyMismatchError(f"Can't find Process #{process.id} ({str(sync_key)})")


def _check_no_running_steps(process: ActionProcess) -> None:
    if repo.retrieve_running_step_ids(process_id=process.id):
        raise WizardOperationError("There is a running step.")


def _check_all_steps_completed(process: ActionProcess) -> None:
    for step in repo.retrieve_steps(process_id=process.id):
        if step.state != ProcessStepState.COMPLETED:
            raise WizardOperationError("All steps must be completed.")
