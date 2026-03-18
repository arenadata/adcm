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

from functools import partial
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field, model_validator

from core.bundle._parsing.shared.config import ConfigAsListDictOrNoneNoDuplicates
from core.bundle._parsing.shared.model import BundleModel
from core.bundle._parsing.shared.validation import (
    field_not_set_mode_before,
    min_and_max_present,
    upgrade_scripts_are_valid,
)
from core.bundle._parsing.v_2_0.actions import (
    AnsibleScript,
    BeforeUpgradeCleanScript,
    BundleRevertInternalScript,
    BundleSwitchInternalScript,
    ConfigApplyInternalScript,
    StateActionResultSchema,
)
from core.bundle._parsing.v_2_0.schema import Masking, ScriptsTemplate, StatesSchema, VersionsSchema

_SwitchRevertCleanScripts = BundleSwitchInternalScript | BundleRevertInternalScript | BeforeUpgradeCleanScript
UpgradeCommonInternalScript = Annotated[_SwitchRevertCleanScripts, Field(discriminator="script")]
UpgradeDynamicInternalScript = Annotated[
    _SwitchRevertCleanScripts | ConfigApplyInternalScript, Field(discriminator="script")
]
# extra validator is added to not duplicate scripts structure, yet it's not allowed in upgrade
UpgradeScript = Annotated[
    UpgradeCommonInternalScript | AnsibleScript,
    Field(discriminator="script_type"),
    BeforeValidator(partial(field_not_set_mode_before, field_name="allow_to_terminate")),
]
UpgradeDynamicScript = Annotated[
    UpgradeDynamicInternalScript | AnsibleScript,
    Field(discriminator="script_type"),
    BeforeValidator(partial(field_not_set_mode_before, field_name="allow_to_terminate")),
    AfterValidator(upgrade_scripts_are_valid),
]


class SimpleUpgrade(BundleModel):
    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    ui_options: Annotated[dict | None, Field(default=None)]

    versions: Annotated[VersionsSchema, AfterValidator(min_and_max_present)]
    from_edition: Annotated[str | list[str] | None, Field(default=None)]

    states: Annotated[StatesSchema | None, Field(default=None)]


class _UpgradeWithActionBase(SimpleUpgrade):
    config: ConfigAsListDictOrNoneNoDuplicates

    masking: Masking
    on_fail: Annotated[StateActionResultSchema | None, Field(default=None)]
    on_success: Annotated[StateActionResultSchema | None, Field(default=None)]

    @model_validator(mode="after")
    def exclusive_masking_and_states(self):
        any_masking_field_set = any(x is not None for x in (self.masking, self.on_success, self.on_fail))

        if any_masking_field_set and self.states:
            raise ValueError("Masking fields and states are mutually exclusive for upgrade")

        return self


class UpgradeWithScripts(_UpgradeWithActionBase):
    scripts: list[UpgradeScript]


class UpgradeWithScriptsTemplate(_UpgradeWithActionBase):
    scripts_template: ScriptsTemplate


ProviderUpgrades = Annotated[list[UpgradeWithScripts | SimpleUpgrade] | None, Field(default=None)]
ClusterUpgrades = Annotated[
    list[UpgradeWithScriptsTemplate | UpgradeWithScripts | SimpleUpgrade] | None, Field(default=None)
]
