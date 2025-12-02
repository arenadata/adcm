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

from core.legacy.bundle_alt.errors import BundleValidationError
from core.legacy.job.types import JobSpec, MappingRule
from core.templates._errors import RenderError
from core.types import ActionID, ActionProcessID, ActionProcessStepID, CoreObjectDescriptor

from cm.converters import core_type_to_model
from cm.errors import AdcmEx
from cm.legacy.services.action_process import repo
from cm.legacy.services.action_process.types import DBPrototypeConfig, ProcessStepState, StepType, StepUpdateDTO
from cm.legacy.services.bundle_alt.render import ActionArgs, Environment, TaskArgs, render_config, render_scripts
from cm.legacy.services.bundle_alt.render._render import render_hc_template
from cm.logger import logger


@dataclass(frozen=True, slots=True)
class RenderStepContext:
    process_id: ActionProcessID
    action_id: ActionID
    object: CoreObjectDescriptor


def fill_step_spec(step_id: ActionProcessStepID, context: RenderStepContext) -> None:
    try:
        spec = _render_step(step_id=step_id, context=context)
        repo.update_step(step_id=step_id, data=StepUpdateDTO(step_spec=spec))
    except (RenderError, AdcmEx, BundleValidationError):
        logger.exception(f"Failed to render step {step_id}")
        repo.update_step(step_id=step_id, data=StepUpdateDTO(state=ProcessStepState.BROKEN))


def _render_step(
    step_id: ActionProcessStepID, context: RenderStepContext
) -> list[JobSpec] | list[DBPrototypeConfig] | list[MappingRule]:
    process = repo.retrieve_process(process_id=context.process_id)
    step = repo.retrieve_step(process_id=context.process_id, step_id=step_id)
    template = repo.find_step_spec_declaration(step=step, process_flow_spec=process.flow_spec).template

    process_orm = repo.retrieve_process_orm(process_id=process.id)
    action_orm = repo.retrieve_action_orm(action_id=context.action_id)
    object_orm = core_type_to_model(context.object.type).objects.get(id=context.object.id)
    bundle_root = repo.get_bundle_root_from_prototype(prototype_id=object_orm.prototype_id)
    environment = Environment(bundle_root=bundle_root)

    match step.type:
        case StepType.CONFIGURATION:
            action_args = ActionArgs(
                action=action_orm,
                cluster_relative_object=object_orm,
                action_process=process_orm,
            )
            prototype_configs = render_config(template=template, environment=environment, context_args=action_args)
            step_spec = repo.serialize_prototype_configs(data=prototype_configs)

        case StepType.OPERATION:
            task_args = TaskArgs(
                target_object=object_orm,
                action=action_orm,
                config={},
                verbose=False,
                delta=None,
                action_process=process_orm,
            )
            step_spec = render_scripts(template=template, environment=environment, context_args=task_args)

        case StepType.MAPPING:
            task_args = TaskArgs(
                target_object=object_orm,
                action=action_orm,
                config={},
                verbose=False,
                delta=None,
                action_process=process_orm,
            )
            step_spec = render_hc_template(template=template, environment=environment, context_args=task_args)

        case _:
            raise NotImplementedError(f"Unexpected step type {step.type}")

    return step_spec
