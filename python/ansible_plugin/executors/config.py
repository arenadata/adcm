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

from cm.api import set_object_config_with_plugin
from cm.converters import core_type_to_model
from cm.models import ConfigLog
from cm.services.config import ConfigAttrPair
from cm.services.config.spec import FlatSpec, retrieve_flat_spec_for_objects
from cm.status_api import send_config_creation_event
from core.types import CoreObjectDescriptor
from django.db.transaction import atomic
from pydantic import model_validator
from typing_extensions import Self

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseStrictModel,
    BaseTypedArguments,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
    TargetConfig,
    from_arguments_root,
)
from ansible_plugin.errors import PluginIncorrectCallError, PluginTargetDetectionError
from ansible_plugin.executors._validators import validate_target_allowed_for_context_owner
from ansible_plugin.utils import cast_to_type

# don't want to typehint due to serialization problems and serialization priority
# (e.g. bool casted successfully to float, etc.)
ParamValue: TypeAlias = Any
OriginalValues: TypeAlias = ConfigAttrPair


class ParameterToChange(BaseStrictModel):
    key: str
    value: ParamValue = None
    active: bool | None = None

    @model_validator(mode="after")
    def check_one_is_specified(self) -> Self:
        if self.model_fields_set.issuperset({"active", "value"}):
            message = "Could use only `value` or `active`, not both"
            raise ValueError(message)

        return self

    @model_validator(mode="after")
    def check_either_value_or_active(self) -> Self:
        if not self.model_fields_set.intersection({"active", "value"}):
            message = "Either `value` or `active` should be specified"
            raise ValueError(message)

        return self


class ChangeConfigArguments(ParameterToChange, BaseTypedArguments):
    # new API to change multiple parameters
    parameters: list[ParameterToChange] | None = None

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


class ChangeConfigReturn(TypedDict):
    value: dict[str, ParamValue] | ParamValue


class ADCMConfigPluginExecutor(ADCMAnsiblePluginExecutor[ChangeConfigArguments, ChangeConfigReturn]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=ChangeConfigArguments),
        target=TargetConfig(detectors=(from_arguments_root,)),
    )

    @atomic()
    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: ChangeConfigArguments, runtime: RuntimeEnvironment
    ) -> CallResult[ChangeConfigReturn]:
        target, *_ = targets

        if error := validate_target_allowed_for_context_owner(context_owner=runtime.context_owner, target=target):
            return CallResult(value={}, changed=False, error=error)

        changes = ConfigAttrPair(config={}, attr={})
        for parameter in arguments.parameters or [arguments]:
            key = parameter.key
            if "/" not in key:
                key = f"{key}/"

            if parameter.active is not None:
                changes.attr[key] = {"active": parameter.active}
            else:
                changes.config[key] = parameter.value

        return_value = self._prepare_return_value(changes.config)

        model = core_type_to_model(core_type=target.type)
        try:
            db_object = model.objects.select_related("config").get(id=target.id)
        except model.DoesNotExist:
            return CallResult(
                value=None, changed=False, error=PluginTargetDetectionError(message=f"Failed to find {target=}")
            )

        configuration = ConfigAttrPair(**ConfigLog.objects.values("config", "attr").get(id=db_object.config.current))
        spec = next(iter(retrieve_flat_spec_for_objects(prototypes=(db_object.prototype_id,)).values()))

        changed = _fill_config_and_attr(target=configuration, changes=changes, spec=spec)

        if not changed:
            return CallResult(value=return_value, changed=False, error=None)

        set_object_config_with_plugin(obj=db_object, config=configuration.config, attr=configuration.attr)
        send_config_creation_event(object_=db_object)

        return CallResult(value=return_value, changed=True, error=None)

    @staticmethod
    def _prepare_return_value(config: dict) -> ChangeConfigReturn:
        # todo what should be returned in `value`??
        #  originally the same data that was passed was returned
        #  WITHOUT type casting
        if len(config) == 1:
            config_params = next(iter(config.values()))
        else:
            # removing trailing "/" to return to keys to input format
            config_params = {key.rstrip("/"): value for key, value in config.items()}

        # putting result under the "value" key, because during result parsing dicts are merged into response,
        # return of this plugin should always have `value` key
        return ChangeConfigReturn(value=config_params)


def _fill_config_and_attr(target: ConfigAttrPair, changes: ConfigAttrPair, spec: FlatSpec) -> bool:
    """
    Fill `target` with values from `changes` in-place

    :param target: Values for complex structures are nested (e.g. ["groupkey"]["valingorupkey"])
    :param changes: Keys must have the same format as flatspec (e.g. ["groupkey/subgroupkey"])
    :param spec: Flat specification for the changing config
    :returns: Changed flag that's true if either param in config/attr has changed
    """

    keys_to_change = set(changes.config.keys()) | set(changes.attr.keys())
    if missing_keys := keys_to_change - spec.keys():
        message = f"Some keys aren't presented in specification: {', '.join(sorted(missing_keys))}"
        raise PluginIncorrectCallError(message=message)

    changed = False

    for key, value in changes.config.items():
        param_spec = spec[key]
        cast_value = cast_to_type(field_type=param_spec.type, value=value, limits=param_spec.limits)

        key, *subs = key.split("/", maxsplit=1)
        subkey = subs[0] if subs else None

        if subkey:
            if target.config[key][subkey] == cast_value:
                continue

            target.config[key][subkey] = cast_value
            changed = True
        else:
            if target.config[key] == cast_value:
                continue

            target.config[key] = cast_value
            changed = True

    # here we consider key full key
    for key, value in changes.attr.items():
        param_spec = spec[key]
        if "activatable" not in param_spec.limits:
            message = (
                "`active` parameter can be changed only for activatable group. " f"Group {key} is not one of them."
            )
            raise PluginIncorrectCallError(message=message)

        attr_key = key.rstrip("/")
        # we want to directly compare "active"'s since it's the only thing we may change via plugin
        if target.attr[attr_key].get("active") == value["active"]:
            continue

        target.attr[attr_key] |= value
        changed = True

    return changed
