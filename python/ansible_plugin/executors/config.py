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

from typing import Any, Collection, TypeAlias, TypedDict
import re

from application.migration.config import update_configuration_from_job
from cm.converters import core_type_to_model
from core.bundle_alt.schema import ConfigApplyParameterItem
from core.types import CoreObjectDescriptor
from django.db.transaction import atomic
from infra.services import get_config_service
from pydantic import model_validator
from typing_extensions import Self
import core

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseTypedArguments,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
    TargetConfig,
    from_arguments_root,
)
from ansible_plugin.executors._validators import validate_target_allowed_for_context_owner

# don't want to typehint due to serialization problems and serialization priority
# (e.g. bool casted successfully to float, etc.)
ParamValue: TypeAlias = Any

INTEGER_LIKE_STRING = re.compile(r"^\d+$")
FLOAT_LIKE_STRING = re.compile(r"^\d+\.\d+$")


class AdcmConfigParameterPluginItem(ConfigApplyParameterItem):
    value: Any = None
    active: bool | None = None

    @model_validator(mode="after")
    def check_one_is_specified(self):
        if self.model_fields_set.issuperset({"active", "value"}):
            message = "Could use only `value` or `active`, not both"
            raise ValueError(message)

        return self

    @model_validator(mode="after")
    def check_either_value_or_active(self):
        if not self.model_fields_set.intersection({"active", "value"}):
            message = "Either `value` or `active` should be specified"
            raise ValueError(message)

        return self


class ChangeAdcmConfigArguments(AdcmConfigParameterPluginItem, BaseTypedArguments):
    # new API to change multiple parameters
    parameters: list[AdcmConfigParameterPluginItem] | None = None

    # not required for old API for changing one parameter
    key: str | None = None

    @model_validator(mode="after")
    def check_either_single_or_multi_parameters(self) -> Self:
        if "parameters" in self.model_fields_set:
            if self.model_fields_set.intersection({"key", "value", "active"}):
                message = "`parameters` can't be used with `key`/`value`/`active`"
                raise ValueError(message)
        elif not (self.key and self.model_fields_set.intersection({"active", "value"})):
            message = "`key` should be specified with `active` or `value` when `parameters` aren't"
            raise ValueError(message)

        return self

    @model_validator(mode="after")
    def check_either_value_or_active(self) -> Self:
        # check is moved to `check_either_single_or_multi_parameters`
        return self

    def get_changes(self) -> list[dict]:
        return [
            {"key": parameter.key, "value": parameter.value, "active": parameter.active}
            for parameter in self.parameters or [self]
        ]


class ChangeConfigReturn(TypedDict):
    value: dict[str, ParamValue] | ParamValue


class ADCMConfigPluginExecutor(ADCMAnsiblePluginExecutor[ChangeAdcmConfigArguments, ChangeConfigReturn]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=ChangeAdcmConfigArguments),
        target=TargetConfig(detectors=(from_arguments_root,)),
    )

    @atomic()
    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: ChangeAdcmConfigArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[ChangeConfigReturn]:
        target, *_ = targets

        if error := validate_target_allowed_for_context_owner(context_owner=runtime.context_owner, target=target):
            return CallResult(value={}, changed=False, error=error)

        config_service = get_config_service()

        original_changes = arguments.get_changes()

        model = core_type_to_model(core_type=target.type)
        db_object = model.objects.get(id=target.id)

        changes, has_changed = update_configuration_from_job(
            owner=target,
            changes_input=original_changes,
            convert=to_flat_configuration,
            description="ansible update",
            job_id=runtime.vars.job.id,
            config_service=config_service,
            owner_orm=db_object,
        )

        return_value = to_return_value(changes=changes)

        return CallResult(value=return_value, changed=has_changed, error=None)


def to_flat_configuration(input_changes: list[dict], spec: core.config.spec.FullSpec) -> core.config.FlatConfiguration:
    target = core.config.FlatConfiguration()

    for parameter_change in input_changes:
        full_name = core.config.names.ensure_full_name(parameter_change["key"])

        if (is_active := parameter_change.get("active")) is not None:
            target.attributes[full_name] = core.config.Attributes(is_active=is_active)
        else:
            raw_value = parameter_change["value"]
            if not isinstance(raw_value, str):
                target.values[full_name] = raw_value
            else:
                parameter = spec.parameters.get(full_name)
                parsed_value = parse_string_value(value=raw_value, parameter=parameter)
                target.values[full_name] = parsed_value

    return target


def to_return_value(changes: core.config.FlatConfiguration) -> ChangeConfigReturn:
    values = changes.values

    if len(values) == 1:
        config_params = next(iter(values.values()))
    else:
        # removing trailing and prefixing "/" to return to keys to input format
        config_params = {key.strip("/"): value for key, value in values.items()}

    # putting result under the "value" key, because during result parsing dicts are merged into response,
    # return of this plugin should always have `value` key
    return ChangeConfigReturn(value=config_params)


def parse_string_value(value: str, parameter: core.config.spec.p.SimpleParameter) -> int | float | str | bool:
    # shortcut for most generic case
    if parameter.type == core.config.spec.p.ParameterType.STRING:
        return value

    match parameter:
        case core.config.spec.p.NumberParameter(is_float=is_float):
            if is_float:
                return float(value)

            return int(value)

        # case core.config.spec.p.BooleanParameter():
        #    truth_literal = "true"
        #    lower_value = value.lower()
        #    if lower_value not in (truth_literal, "false"):
        #        raise ValueError(f"can't parse {value} as boolean")

        #    return value == "true"

        case core.config.spec.p.OptionParameter(options=options):
            # strange patch retrieved from original plugin
            if value in options.values():
                return value

            if INTEGER_LIKE_STRING.match(value):
                return int(value)

            if FLOAT_LIKE_STRING.match(value):
                return float(value)

    return value
