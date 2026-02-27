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

from core import templates
from core.dynamic_bundle.render import BundleRenderer
from core.templates import RenderError
from core.types import ActionProcessID, ActionProcessStepID
import core

from cm.errors import AdcmEx
from cm.legacy.services.action_process import repo
from cm.legacy.services.action_process.types import ProcessContext, ProcessStepState, StepUpdateDTO
from cm.legacy.services.bundle_alt.render import ActionArgs, TaskArgs
from cm.logger import logger


@dataclass(frozen=True, slots=True)
class RenderStepContext:
    process_id: ActionProcessID
    process_context: ProcessContext


def fill_step_spec(
    step_id: ActionProcessStepID,
    context: RenderStepContext,
    bundle_renderer: BundleRenderer[ActionArgs, TaskArgs],
    wizard_repo: core.action.wizard.WizardRepoI,
) -> None:
    try:
        process = wizard_repo.retrieve_process(process_id=context.process_id)
        step = wizard_repo.retrieve_step(process_id=context.process_id, step_id=step_id)
        template = core.action.wizard.operations.find_step_spec_declaration(
            step=step, process_flow_spec=process.flow_spec
        ).template
        bundle_context = repo.get_bundle_context_from_prototype(
            prototype_id=context.process_context.action.owner_prototype.id
        )

        spec = _render_step(
            template=template,
            step_type=step.type,
            process_id=process.id,
            render_context=context,
            bundle_context=bundle_context,
            bundle_renderer=bundle_renderer,
        )

        wizard_repo.update_step(step_id=step_id, data=StepUpdateDTO(step_spec=spec))

    except (RenderError, AdcmEx, core.bundle.BundleValidationError, core.bundle.BundleParsingError):
        logger.exception(f"Failed to render step {step_id}")
        wizard_repo.update_step(step_id=step_id, data=StepUpdateDTO(state=ProcessStepState.BROKEN))


def _render_step(
    template: templates.Template,
    step_type: core.action.wizard.StepType,
    process_id: core.action.wizard.ProcessID,
    render_context: RenderStepContext,
    bundle_context: core.bundle.BundleContext,
    bundle_renderer: BundleRenderer[ActionArgs, TaskArgs],
) -> core.action.wizard.ConfigStepSpec | core.action.wizard.OperationStepSpec | core.action.wizard.MappingStepSpec:
    action_args = ActionArgs(
        action=render_context.process_context.action_orm,
        owner_object=render_context.process_context.owner_orm,
        target_object=render_context.process_context.target_orm,
        wizard_process_id=process_id,
    )
    match step_type:
        case core.action.wizard.StepType.CONFIGURATION:
            step_spec = bundle_renderer.render_config(
                template=template, args=action_args, bundle_context=bundle_context
            )

        case core.action.wizard.StepType.OPERATION:
            args = TaskArgs.from_action_args(action_args)
            args.config = {}
            allow_to_terminate = render_context.process_context.action_orm.allow_to_terminate
            step_spec = bundle_renderer.render_scripts_for_wizard(
                template=template,
                args=args,
                bundle_context=bundle_context,
                action_allow_to_terminate=allow_to_terminate,
            )

        case core.action.wizard.StepType.MAPPING:
            args = TaskArgs.from_action_args(action_args)
            args.config = {}
            step_spec = bundle_renderer.render_mapping_rules(
                template=template, args=args, bundle_context=bundle_context
            )

    return step_spec
