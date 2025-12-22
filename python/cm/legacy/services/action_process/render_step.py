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
from core.legacy.job.types import JobSpec
from core.mapping import MappingRule
from core.templates._errors import RenderError
from core.types import ActionID, ActionProcessID, ActionProcessStepID, CoreObjectDescriptor, PrototypeID
import core

from cm.converters import core_type_to_model
from cm.errors import AdcmEx
from cm.legacy.services.action_process import repo
from cm.legacy.services.action_process.types import DBPrototypeConfig, ProcessStepState, StepUpdateDTO
from cm.legacy.services.bundle_alt.render import (
    ActionArgs,
    ContextGatherer,
    Environment,
    TaskArgs,
    render_config,
    render_hc_template,
    render_scripts,
)
from cm.logger import logger


@dataclass(frozen=True, slots=True)
class RenderStepContext:
    process_id: ActionProcessID
    action_id: ActionID
    target: CoreObjectDescriptor
    owner_prototype_id: PrototypeID


def fill_step_spec(step_id: ActionProcessStepID, context: RenderStepContext, context_gatherer: ContextGatherer) -> None:
    try:
        spec = _render_step(step_id=step_id, context=context, context_gatherer=context_gatherer)
        repo.update_step(step_id=step_id, data=StepUpdateDTO(step_spec=spec))
    except (RenderError, AdcmEx, BundleValidationError):
        logger.exception(f"Failed to render step {step_id}")
        repo.update_step(step_id=step_id, data=StepUpdateDTO(state=ProcessStepState.BROKEN))


def _render_step(
    step_id: ActionProcessStepID, context: RenderStepContext, context_gatherer: ContextGatherer
) -> list[JobSpec] | list[DBPrototypeConfig] | list[MappingRule]:
    process = repo.retrieve_process(process_id=context.process_id)
    step = repo.retrieve_step(process_id=context.process_id, step_id=step_id)
    template = repo.find_step_spec_declaration(step=step, process_flow_spec=process.flow_spec).template

    action_orm = repo.retrieve_action_orm(action_id=context.action_id)
    target_orm = core_type_to_model(context.target.type).objects.get(id=context.target.id)
    bundle_root = repo.get_bundle_root_from_prototype(prototype_id=context.owner_prototype_id)
    environment = Environment(bundle_root=bundle_root)

    match step.type:
        case core.action.wizard.StepType.CONFIGURATION:
            action_args = ActionArgs(
                action=action_orm,
                cluster_relative_object=target_orm,
                wizard_process_id=process.id,
            )
            prototype_configs = render_config(
                template=template, environment=environment, context_args=action_args, context_gatherer=context_gatherer
            )
            step_spec = repo.serialize_prototype_configs(data=prototype_configs)

        case core.action.wizard.StepType.OPERATION:
            task_args = TaskArgs(
                target_object=target_orm,
                action=action_orm,
                config={},
                verbose=False,
                delta=None,
                wizard_process_id=process.id,
            )
            step_spec = render_scripts(
                template=template, environment=environment, context_args=task_args, context_gatherer=context_gatherer
            )

        case core.action.wizard.StepType.MAPPING:
            task_args = TaskArgs(
                target_object=target_orm,
                action=action_orm,
                config={},
                verbose=False,
                delta=None,
                wizard_process_id=process.id,
            )
            step_spec = render_hc_template(
                template=template, environment=environment, context_args=task_args, context_gatherer=context_gatherer
            )

    return step_spec
