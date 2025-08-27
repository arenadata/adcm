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

from typing import Any, Literal, TypeAlias
from uuid import uuid4
import logging

from adcm.mixins import ParentObject
from core.bundle_alt.process import ScriptsConversionContext, parse_scripts
from core.job.dto import LogCreateDTO, TaskPayloadDTO
from core.job.types import ActionInfo
from core.templates import RendererEnv, Template, get_renderer
from core.types import ActionID, ActionProcessID, ActionProcessStepID, ActionTargetDescriptor, CoreObjectDescriptor
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.utils import timezone

from cm.converters import core_type_to_model, orm_object_to_core_descriptor
from cm.models import Process, ProcessStep, ProcessStepInput
from cm.services.concern.flags import BuiltInFlag, lower_flag
from cm.services.config import ConfigAttrPair
from cm.services.jinja_env import get_env_for_jinja_config
from cm.services.job.run import start_task
from cm.services.job.run.repo import JobRepoImpl
from cm.services.wizard import repo, stage
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


def render_template(
    template: Template, environment: RendererEnv, action_id: ActionID, object_: CoreObjectDescriptor
) -> Any:
    renderer = get_renderer(template=template, environment=environment)
    # TODO: replace with correct context retriever; handle render error
    orm_object = core_type_to_model(object_.type).objects.get(pk=object_.id)
    context = get_env_for_jinja_config(
        action=repo.retrieve_action_orm(action_id=action_id), cluster_relative_object=orm_object
    )
    return renderer.render(context=context)


def initiate_process(object_: CoreObjectDescriptor, action: ActionInfo) -> ActionProcessID:
    environment = RendererEnv(
        discovery_root=repo.get_bundle_root_from_prototype(prototype_id=action.owner_prototype.id)
    )
    stages_raw = render_template(
        template=action.wizard_template, environment=environment, action_id=action.id, object_=object_
    )
    stages = stage.convert_stages(stages_raw=stages_raw)

    process = repo.create_process(object_=object_, action_id=action.id, stages=stages)
    repo.create_stages(process_id=process.id, stages=stages)  # TODO: validate stages

    return process.id


def complete_process(process: ActionProcess) -> None:
    # todo add validation + check sync status
    repo.set_process_status(process=process, state=ProcessState.COMPLETED)


def complete_step(step_id: ActionProcessStepID) -> None:
    repo.update_step(step_id=step_id, data=StepUpdateDTO(state=ProcessStepState.COMPLETED))


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
    return ProcessStep.objects.filter(process_id=process_id, id__gt=step_id)


def retrieve_steps_starting_with_qs(process_id: ActionProcessID, step_id: ActionProcessStepID) -> QuerySet:
    """
    Returns a queryset of steps starting from (and including) step_id in the same process.
    """
    return ProcessStep.objects.filter(process_id=process_id, id__gte=step_id)


def retrieve_current_step_id(process_id: ActionProcessID) -> ActionProcessStepID:
    """
    Returns the current step of the specified process.
    """

    flow_spec = Process.objects.get(id=process_id).flow_spec
    step_names_id_map = repo.retrieve_step_names_id_map(process_id=process_id)

    latest = None
    step_ids = []
    for stage_ in reversed(flow_spec):
        for step in reversed(stage_["steps"]):
            step_id = step_names_id_map[step["name"], step["display_name"]]
            step_ids.append(step_id)
            state = ProcessStep.objects.values_list("state", flat=True).get(id=step_id)
            if state in (ProcessStepState.CREATED, ProcessStepState.RUNNING):
                latest = step_id

    if latest is None:
        latest = step_ids[0]

    return latest


def update_process_sync_key(process_id: ActionProcessID) -> None:
    repo.update_process(process_id=process_id, data=ProcessUpdateDTO(sync_key=uuid4()))


def set_process_last_completed_step(process_id: ActionProcessID, step_id: ActionProcessStepID) -> None:
    repo.update_process(process_id=process_id, data=ProcessUpdateDTO(last_completed_step=step_id))


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


def perform_operation(
    process_id: ActionProcessID,
    payload: OperationPayload,
    object_: ParentObject,
    action: ActionInfo,
    # TODO: config converter arg
) -> None:
    update_process_sync_key(process_id=process_id)
    process = repo.retrieve_process(process_id=process_id)

    match payload.method:
        case ProcessOperationType.SUBMIT:
            step = repo.retrieve_step(process_id=process_id, step_id=payload.params.step_id)

            match step.type:
                case StepType.CONFIGURATION:
                    config: ConfigAttrPair = _prepare_step_config_input(
                        process_id=process_id, step_id=payload.params.step_id, config=payload.params.configuration
                    )
                    _operation_submit_config(
                        process=process,
                        step_id=payload.params.step_id,
                        configuration=config,
                        parent_object=object_,
                        action=action,
                    )

                    complete_step(step_id=step.id)
                    set_process_last_completed_step(process_id=process_id, step_id=step.id)

                case StepType.OPERATION:  # TODO: extract step/process update from operations
                    _operation_submit_job(
                        process=process, step_id=payload.params.step_id, parent_object=object_, action=action
                    )

        case ProcessOperationType.RESET:
            _operation_reset(process=process, step_id=payload.params.step_id)
            set_process_last_completed_step(process_id=process_id, step_id=payload.params.step_id)

        case ProcessOperationType.COMPLETE:
            complete_process(process=process)
            lower_flag(
                BuiltInFlag.WIZARD_PROCESS_RUNNING.value.name,
                on_objects=[orm_object_to_core_descriptor(object_=object_)],
            )


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


@atomic
def _operation_reset(process: ActionProcess, step_id: ActionProcessStepID) -> None:
    revoke_starting_with_step(process.id, step_id)
    # Here we rely on process steps bulk_create behavior:
    # ids of created rows are preserves the definition order in process.flow_spec
    # so min(revoked_steps) is previous step
    last_completed_step_id = ProcessStep.objects.filter(state=ProcessStepState.COMPLETED).order_by("-id").first()
    Process.objects.filter(id=process.id).update(sync_key=uuid4(), last_completed_step_id=last_completed_step_id)


@atomic
def _operation_submit_job(
    process: ActionProcess,
    step_id: int,
    *,
    parent_object: ParentObject,  # target == owner, Cluster, Service, Component, Provider, Host / ???ActionHostGroup???
    action: ActionInfo,
) -> None:
    step = repo.retrieve_step(process_id=process.id, step_id=step_id)

    job_repo = JobRepoImpl

    owner = orm_object_to_core_descriptor(object_=parent_object)  # target == owner
    target = ActionTargetDescriptor(id=owner.id, type=owner.type)
    payload = TaskPayloadDTO()

    task = job_repo.create_task(target=target, owner=owner, action=action, payload=payload)
    logging.getLogger("adcm").error(f"{task.action=}")

    process_ = repo.retrieve_process(process_id=process.id)

    step_raw_spec = repo.find_step_spec(step=step, process_flow_spec=process_.flow_spec)

    bundle_root_path = repo.get_bundle_root_from_prototype(prototype_id=parent_object.prototype_id)
    action_orm = repo.retrieve_action_orm(action_id=action.id)  # ???
    context = ScriptsConversionContext(
        source_dir=bundle_root_path / step_raw_spec.template.file.path,
        action_allow_to_terminate=action_orm.allow_to_terminate,
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
    ProcessStep.objects.filter(id=step_id).update(state=ProcessStepState.RUNNING)
    Process.objects.filter(id=process.id).update(sync_key=uuid4(), last_completed_step_id=step_id)

    # todo write pid to task (executor)
    start_task(task=task_orm)


@atomic
def _operation_submit_config(
    process: ActionProcess,
    step_id: ActionProcessStepID,
    configuration: ConfigAttrPair,
    *,
    parent_object: ParentObject,
    action: ActionInfo,
) -> None:
    _ = parent_object, action

    data = {"step_id": step_id, "configuration": configuration._asdict(), "job": None, "created_at": timezone.now()}
    step_input_qs = ProcessStepInput.objects.filter(step_id=step_id)

    if not step_input_qs.exists():
        ProcessStepInput.objects.create(**data)
    else:
        step_input_qs.update(**data)

    revoke_next_steps(process_id=process.id, step_id=step_id)
