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
from typing import Annotated

from pydantic import Field, model_validator

from core import action
from core.bundle._parsing.shared.model import BundleModel
from core.bundle._parsing.shared.templates import ConfigTemplate, HCTemplate, ScriptsTemplate, Template


class _Names(BundleModel):
    name: str
    display_name: str


class _BaseStep(_Names):
    description: Annotated[str, Field(default="")]
    required: Annotated[bool, Field(default=True)]

    @property
    @abstractmethod
    def type(self) -> action.wizard.StepType:
        ...

    @model_validator(mode="after")
    def validate_required_flag(self):
        if not self.required and self.type != action.wizard.StepType.OPERATION:
            raise ValueError(f"{self.type} type step can't be non-required.")
        return self


class OperationStep(_BaseStep):
    scripts_template: ScriptsTemplate
    ui_options: action.wizard.OperationUIOptions

    @property
    def type(self) -> action.wizard.StepType:
        return action.wizard.StepType.OPERATION

    @property
    def template(self) -> Template:
        return self.scripts_template


class ConfigurationStep(_BaseStep):
    config_template: ConfigTemplate

    @property
    def type(self) -> action.wizard.StepType:
        return action.wizard.StepType.CONFIGURATION

    @property
    def template(self) -> Template:
        return self.config_template


class MappingStep(_BaseStep):
    hc_template: HCTemplate

    @property
    def type(self) -> action.wizard.StepType:
        return action.wizard.StepType.MAPPING

    @property
    def template(self) -> Template:
        return self.hc_template


WizardProcessStep = OperationStep | ConfigurationStep | MappingStep


class WizardProcessStage(_Names):
    description: Annotated[str, Field(default="")]
    steps: list[WizardProcessStep] = Field(..., min_length=1, description="At least one step is required in a stage")

    @model_validator(mode="after")
    def steps_names_are_unique(self):
        step_names = set()
        for step in self.steps:
            if step.name in step_names:
                raise ValueError(f"Duplicate step name: {step.name}")

            step_names.add(step.name)

        return self
