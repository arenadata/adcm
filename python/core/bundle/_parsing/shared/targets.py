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

from pydantic import RootModel, model_validator

from core import mapping
from core.bundle._parsing.shared.wizard import WizardProcessStage

# Mapping


MappingRules = RootModel[list[mapping.MappingRule]]

# Wizard


class ActionWizardStages(RootModel[list[WizardProcessStage]]):
    @model_validator(mode="after")
    def stage_names_are_unique(self):
        stage_names = set()
        for stage in self.root:
            if stage.name in stage_names:
                raise ValueError(f"Duplicate stage name: {stage.name}")

            stage_names.add(stage.name)

        return self
