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

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, model_validator

from core.bundle._parsing.shared.config import ConfigAsListDictOrNoneNoDuplicates
from core.bundle._parsing.shared.validation import min_and_max_present
from core.bundle._parsing.v_2_0.actions import (
    AnsibleScript,
    BundleRevertInternalScript,
    BundleSwitchInternalScript,
    StateActionResultSchema,
)
from core.bundle._parsing.v_2_0.schema import Masking, StatesSchema, VersionsSchema

BundleSwitchOrRevertInternalScript = Annotated[
    BundleSwitchInternalScript | BundleRevertInternalScript, Field(discriminator="script")
]
UpgradeScript = Annotated[BundleSwitchOrRevertInternalScript | AnsibleScript, Field(discriminator="script_type")]


class SimpleUpgrade(BaseModel):
    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    ui_options: Annotated[dict | None, Field(default=None)]

    versions: Annotated[VersionsSchema, AfterValidator(min_and_max_present)]
    from_edition: Annotated[str | list[str] | None, Field(default=None)]

    states: Annotated[StatesSchema | None, Field(default=None)]


class UpgradeWithAction(SimpleUpgrade):
    config: ConfigAsListDictOrNoneNoDuplicates

    scripts: Annotated[list[UpgradeScript] | None, Field(default=None)]

    masking: Masking
    on_fail: Annotated[StateActionResultSchema | None, Field(default=None)]
    on_success: Annotated[StateActionResultSchema | None, Field(default=None)]

    @model_validator(mode="after")
    def exclusive_masking_and_states(self):
        any_masking_field_set = any(x is not None for x in (self.masking, self.on_success, self.on_fail))

        if any_masking_field_set and self.states:
            raise ValueError("Masking fields and states are mutually exclusive for upgrade")

        return self


Upgrades = Annotated[list[UpgradeWithAction | SimpleUpgrade] | None, Field(default=None)]
