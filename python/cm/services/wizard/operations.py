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

from core.job.types import ActionInfo, WizardTemplate
from core.templates import RendererEnv, get_renderer
from core.types import ActionID, ActionProcessID, ActionProcessStepID, CoreObjectDescriptor
from django.db.models import QuerySet

from cm.converters import core_type_to_model
from cm.models import ProcessState, ProcessStep, ProcessStepInput, ProcessStepState
from cm.services.jinja_env import get_env_for_jinja_config
from cm.services.wizard import repo, stage
from cm.services.wizard.types import ProcessToChangeDTO

SerializedConfigStep: TypeAlias = dict[
    Literal["configuration"], dict[Literal["config_schema", "adcm_meta", "config"], dict | None]
]
SerializedOperationStep: TypeAlias = dict[Literal["ui_options", "task"], dict | None]


def render_template(
    template: WizardTemplate, environment: RendererEnv, action_id: ActionID, object_: CoreObjectDescriptor
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


# def serialize_step(
#    process_id: ActionProcessID, step_id: ActionProcessStepID, action_id: ActionID, object_: CoreObjectDescriptor
# ) -> SerializedConfigStep | SerializedOperationStep:
#    process = repo.retrieve_process(process_id=process_id)
#    step = repo.retrieve_step(process_id=process_id, step_id=step_id)
#    step_spec_raw = repo.find_step_spec(step=step, process_flow_spec=process.flow_spec)
#
#    if step.is_render_required:
#        _render_step_from_flow_spec(step=step, step_spec_raw=step_spec_raw, action_id=action_id, object_=object_)
#        step = repo.retrieve_step(process_id=process_id, step_id=step_id)
#
#    # TODO: merge with StepInput if exists
#
#    match step.type:
#        case StepType.CONFIGURATION:
#            return _serialize_config_step(step=step, step_spec_raw=step_spec_raw, action_id=action_id, object_=object_)
#        case StepType.OPERATION:
#            return _serialize_operation_step(step_spec_raw=step_spec_raw)
#        case _:
#            raise NotImplementedError(f"Can't serialize {step.type} step.")
#
#
# def _serialize_config_step(
#    step: Step, step_spec_raw: WizardStep, action_id: ActionID, object_: CoreObjectDescriptor
# ) -> SerializedConfigStep:
#    action_orm = repo.retrieve_action_orm(action_id=action_id)
#    object_orm = core_type_to_model(object_.type).objects.get(pk=object_.id)
#    path_resolver = BundlePathResolver(bundle_hash=action_orm.prototype.bundle.hash)
#    config_file = Path(path_resolver.bundle_root, step_spec_raw.template.file.path)
#
#    prototype_configs, _ = _get_jinja_config_new(
#        data=step.step_spec,
#        action=action_orm,
#        config_file=config_file,
#        resolver=path_resolver,
#        object_=object_orm,
#    )
#
#    schema, config, meta = get_schema_config_meta(
#        object_=object_orm,
#        prototype_configs=prototype_configs,
#        path_resolver=path_resolver,
#    )
#
#    return {"config_schema": schema, "adcm_meta": meta, "config": config}
#
#
# def _serialize_operation_step(step_spec_raw: WizardStep) -> SerializedOperationStep:
#    ui_options = step_spec_raw.model_dump().get("ui_options")
#
#    # TODO: get job based on ProcessStepInput
#    return {"ui_options": ui_options, "job": None}
#
#
# def _render_step_from_flow_spec(
#    step: Step, step_spec_raw: WizardStep, action_id: ActionID, object_: CoreObjectDescriptor
# ) -> None:
#    action = ActionRepoImpl.get_action(id=action_id)
#    environment = RendererEnv(
#        discovery_root=repo.get_bundle_root_from_prototype(prototype_id=action.owner_prototype.id)
#    )
#
#    rendered = render_template(
#        template=step_spec_raw.template, environment=environment, action_id=action.id, object_=object_
#    )
#
#    repo.update_step(step_id=step.id, data=StepUpdateDTO(step_spec=rendered))


def complete_process(process: ProcessToChangeDTO):
    # todo add validation + check sync status
    repo.set_process_status(process=process, state=ProcessState.FINISHED)


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


def _repo_revoke_steps(steps_qs: QuerySet) -> set[int]:
    """
    Deletes inputs and clears specs for the given steps.
    Operates directly on the queryset to avoid loading IDs unnecessarily.
    Returns the set of step IDs revoked.
    """
    step_ids = set(steps_qs.values_list("id", flat=True))
    ProcessStepInput.objects.filter(step_id__in=step_ids).delete()
    ProcessStep.objects.filter(id__in=step_ids).update(state=ProcessStepState.REVOKED, step_spec=None)
    return step_ids
