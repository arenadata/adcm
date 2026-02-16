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
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BeforeValidator, Field, model_validator

from core.bundle._parsing.shared.config import ConfigAsListDictOrNoneNoDuplicates
from core.bundle._parsing.shared.validation import (
    forbidden_mm_actions,
    script_is_correct_path,
)
from core.bundle._parsing.v_2_0.internal_scripts import ConfigApplyParams, HcApplyParams
from core.bundle._parsing.v_2_0.schema import (
    ConfigTemplate,
    Masking,
    Name,
    ScriptsTemplate,
    WizardTemplate,
)

# States, action-specific arguments


@dataclass(slots=True)
class HcAclSchema:
    component: str
    action: Literal["add", "remove"]
    service: Annotated[str | None, Field(default=None)]


@dataclass(slots=True)
class ActionStatesSchema:
    available: list[str] | Literal["any"]
    on_success: Annotated[str | None, Field(default=None)]
    on_fail: Annotated[str | None, Field(default=None)]


@dataclass(slots=True)
class MultiStateSchema:
    set: Annotated[list[str] | None, Field(default=None)]
    unset: Annotated[list[str] | None, Field(default=None)]


@dataclass(slots=True)
class StateActionResultSchema:
    state: Annotated[str | None, Field(default=None)]
    multi_state: Annotated[MultiStateSchema | None, Field(default=None)]


# Scripts


@dataclass(slots=True)
class _BaseScript:
    name: str
    display_name: Annotated[str | None, Field(default=None)]
    allow_to_terminate: Annotated[bool | None, Field(default=None)]
    on_fail: Annotated[StateActionResultSchema | str | None, Field(default=None)]


@dataclass(slots=True)
class AnsibleScript(_BaseScript):
    script_type: Literal["ansible"]
    script: Annotated[str, AfterValidator(script_is_correct_path)]
    params: Annotated[dict | None, Field(default=None)]


@dataclass(slots=True)
class PythonScript(_BaseScript):
    script_type: Literal["python"]
    script: Annotated[str, AfterValidator(script_is_correct_path)]


@dataclass(slots=True)
class BundleSwitchInternalScript(_BaseScript):
    script_type: Literal["internal"]
    script: Literal["bundle_switch"]


@dataclass(slots=True)
class BundleRevertInternalScript(_BaseScript):
    script_type: Literal["internal"]
    script: Literal["bundle_revert"]


@dataclass(slots=True)
class HcApplyInternalScript(_BaseScript):
    script_type: Literal["internal"]
    script: Literal["hc_apply"]
    params: HcApplyParams


@dataclass(slots=True)
class ConfigApplyInternalScript(_BaseScript):
    script_type: Literal["internal"]
    script: Literal["config_apply"]
    params: ConfigApplyParams


@dataclass(slots=True)
class BeforeUpgradeCleanScript(_BaseScript):
    script_type: Literal["internal"]
    script: Literal["before_upgrade_clean"]


ProviderInternalScript = Annotated[
    BundleSwitchInternalScript | BundleRevertInternalScript | BeforeUpgradeCleanScript, Field(discriminator="script")
]

ClusterStaticInternalScript = Annotated[ProviderInternalScript | HcApplyInternalScript, Field(discriminator="script")]

ClusterScript = Annotated[
    ClusterStaticInternalScript | AnsibleScript | PythonScript, Field(discriminator="script_type")
]

ADCMScript = Annotated[AnsibleScript | PythonScript, Field(discriminator="script_type")]
ProviderScript = Annotated[ProviderInternalScript | AnsibleScript | PythonScript, Field(discriminator="script_type")]

_DynamicActionInternalScript = Annotated[
    ClusterStaticInternalScript | ConfigApplyInternalScript, Field(discriminator="script")
]
DynamicActionScript = Annotated[
    _DynamicActionInternalScript | AnsibleScript | PythonScript, Field(discriminator="script_type")
]

_DynamicWizardInternalScript = Annotated[
    ProviderInternalScript | ConfigApplyInternalScript, Field(discriminator="script")
]
DynamicWizardScript = Annotated[
    _DynamicWizardInternalScript | AnsibleScript | PythonScript, Field(discriminator="script_type")
]

# Action


@dataclass(slots=True)
class _ActionBase:
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    ui_options: Annotated[dict | None, Field(default=None)]

    allow_to_terminate: Annotated[bool | None, Field(default=None)]

    states: Annotated[ActionStatesSchema | None, Field(default=None)]
    masking: Masking
    on_fail: Annotated[StateActionResultSchema | str | None, Field(default=None)]
    on_success: Annotated[StateActionResultSchema | None, Field(default=None)]

    config: ConfigAsListDictOrNoneNoDuplicates

    # Has to check it as before mode and key presense,
    # because lots of cases (e.g. in integration tests specify "masking:" without value)
    # has `None` value when key is specified.
    # Surely there's a way to check it with pydantic mechanics, yet this one is easier.
    @model_validator(mode="before")
    @classmethod
    def exclusive_visibility_fields(cls, data: Any):
        if not isinstance(data, dict):
            return data

        states_specified = "states" in data
        masking_specified = "masking" in data

        if states_specified and masking_specified:
            raise ValueError('Action uses both mutual excluding states "states" and "masking"')

        on_fail_success_specified = "on_fail" in data or "on_success" in data
        if not masking_specified and on_fail_success_specified:
            raise ValueError('Action uses "on_success/on_fail" states without "masking"')

        return data


@dataclass(slots=True)
class ClusterObjectAction(_ActionBase):
    scripts: Annotated[list[ClusterScript] | None, Field(default=None)]
    scripts_template: Annotated[ScriptsTemplate | None, Field(default=None)]
    config_template: Annotated[ConfigTemplate | None, Field(default=None)]
    wizard_template: Annotated[WizardTemplate | None, Field(default=None)]

    hc_acl: Annotated[list[HcAclSchema] | None, Field(default=None)]

    allow_in_maintenance_mode: Annotated[bool | None, Field(default=None)]
    allow_for_action_host_group: Annotated[bool, Field(default=None)]
    host_action: Annotated[bool, Field(default=None)]

    @model_validator(mode="after")
    def validate_exactly_one_set_for_scripts(self):
        specified = tuple(filter(None, (self.scripts, self.scripts_template)))
        if len(specified) != 1:
            raise ValueError(
                'Exactly one of "scripts" or "scripts_template" must be provided, ' "not multiple nor neither."
            )

        return self

    @model_validator(mode="after")
    def validate_only_one_set_for_config(self):
        specified = tuple(filter(None, (self.config, self.config_template)))
        if len(specified) > 1:
            raise ValueError('At most one of "config" or "config_template" must be provided.')

        return self

    @model_validator(mode="after")
    def validate_hc_apply_together_hc_acl(self):
        if self.scripts is None:
            return self

        if self.wizard_template is not None:
            return self

        for script in self.scripts:
            if script.script_type == "internal" and script.script == "hc_apply" and self.hc_acl is None:
                raise ValueError('"hc_apply" requires "hc_acl" declaration')

        return self

    @model_validator(mode="after")
    def exclusive_host_action_and_action_host_group(self):
        is_host_action = bool(self.host_action)
        is_allowed_in_host_group = bool(self.allow_for_action_host_group)

        if is_host_action and is_allowed_in_host_group:
            raise ValueError(
                "The allow_for_action_host_group and host_action attributes are mutually exclusive.",
            )

        return self


@dataclass(slots=True)
class ADCMAction(_ActionBase):
    scripts: list[ADCMScript]


@dataclass(slots=True)
class HostAction(_ActionBase):
    scripts: list[ProviderScript]


@dataclass(slots=True)
class ProviderAction(HostAction):
    allow_for_action_host_group: Annotated[bool, Field(default=None)]


# United

ClusterActions = Annotated[
    dict[Name, ClusterObjectAction] | None,
    Field(default=None),
    BeforeValidator(forbidden_mm_actions),
]


HostActions = Annotated[
    dict[Name, HostAction] | None,
    Field(default=None),
]

ProviderActions = Annotated[
    dict[Name, ProviderAction] | None,
    Field(default=None),
]

ADCMActions = Annotated[
    dict[Name, ADCMAction] | None,
    Field(default=None),
]
