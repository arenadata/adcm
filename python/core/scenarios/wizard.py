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

from abc import abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar
import logging

from core import bundle, templates
from core.action import wizard
from core.dynamic_bundle.render import BundleRenderer
from core.types import CoreObjectDescriptor

ActionArgsT = TypeVar("ActionArgsT")
TaskArgsT = TypeVar("TaskArgsT")
logger = logging.getLogger("adcm")


@dataclass(slots=True)
class FillWizardStepSpec(Generic[ActionArgsT, TaskArgsT]):
    wizard_repo: wizard.WizardRepoI
    bundle_renderer: BundleRenderer[ActionArgsT, TaskArgsT]

    @abstractmethod
    def convert_action_args_to_task_args(self, args: ActionArgsT) -> TaskArgsT:
        ...

    @abstractmethod
    def retrieve_extra_errors(self) -> tuple[type[Exception], ...]:
        ...

    def do(
        self,
        *,
        step_id: wizard.StepID,
        step_type: wizard.StepType,
        template: templates.Template,
        bundle_context: bundle.BundleContext,
        owner: CoreObjectDescriptor,
        action_args: ActionArgsT,
        action_allow_to_terminate: bool,
    ) -> None:
        handled_errors = (
            templates.RenderError,
            bundle.BundleValidationError,
            bundle.BundleParsingError,
            *self.retrieve_extra_errors(),
        )

        try:
            match step_type:
                case wizard.StepType.CONFIGURATION:
                    spec = self.bundle_renderer.render_config(
                        template=template, args=action_args, bundle_context=bundle_context, owner=owner
                    )

                case wizard.StepType.OPERATION:
                    task_args = self.convert_action_args_to_task_args(action_args)
                    spec = self.bundle_renderer.render_scripts_for_wizard(
                        template=template,
                        args=task_args,
                        bundle_context=bundle_context,
                        action_allow_to_terminate=action_allow_to_terminate,
                    )

                case wizard.StepType.MAPPING:
                    task_args = self.convert_action_args_to_task_args(action_args)
                    spec = self.bundle_renderer.render_mapping_rules(
                        template=template, args=task_args, bundle_context=bundle_context
                    )

            self.wizard_repo.update_step(step_id=step_id, data=wizard.StepUpdateDTO(step_spec=spec))
        except handled_errors:
            logger.exception(f"Failed to render step {step_id}")
            self.wizard_repo.update_step(
                step_id=step_id,
                data=wizard.StepUpdateDTO(state=wizard.ProcessStepState.BROKEN),
            )
