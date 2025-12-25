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

from typing import TYPE_CHECKING, Any

from adcm_version import compare_prototype_versions

from core import config
from core.bundle._constants import ADCM_MM_ACTION_FORBIDDEN_PROPS_SET, ADCM_SERVICE_ACTION_NAMES_SET, NAME_REGEX
from core.templates import Template

if TYPE_CHECKING:
    from core.bundle._parsing.v_1_0.schema import VersionsSchema


def is_path_correct(raw_path: str) -> bool:
    """
    Return whether given path meets ADCM path description requirements

    >>> this = is_path_correct
    >>> this("relative_to_bundle/path.yaml")
    True
    >>> this("./relative/to/file.yaml")
    True
    >>> this(".secret")
    True
    >>> this("../hack/system")
    False
    >>> this("/hack/system")
    False
    >>> this(".././hack/system")
    False
    >>> this("../../hack/system")
    False
    """
    return raw_path.startswith("./") or not raw_path.startswith(("..", "/"))


def script_is_correct_path(script: str):
    if not is_path_correct(script):
        raise ValueError(f"Action's script has unsupported path format: {script}")

    return script


def validate_name(name: str) -> str:
    if NAME_REGEX.fullmatch(name) is None:
        raise ValueError(
            "Name is incorrect. Only latin characters, digits, "
            "dots (.), dashes (-), and underscores (_) are allowed.",
        )

    return name


def convert_config(config: Any) -> list:
    """Converts old-style dict config to list config"""

    # We expect this validator to be called only if a field is defined in the data.
    if config is None:
        raise ValueError("the value cannot be empty")

    if not isinstance(config, dict):
        return config

    new_config = []
    for key, value in config.items():
        subs = None
        extra = {}

        if value is None:
            # patch very strange stuff when it's None and not dict, cases aren't prod-related
            value = {}
        elif "type" not in value or not isinstance(value["type"], str):  # it is a group
            extra = {"type": "group", "required": False}
            subs = convert_config(value)

        new_value = {"name": key, "subs": subs, **extra} if subs is not None else {"name": key, **value, **extra}
        new_config.append(new_value)

    return new_config


def license_allowed_for_type(type_: str) -> None:
    allowed_types = {"cluster", "service", "provider"}

    if type_ not in allowed_types:
        raise ValueError("License can be placed in cluster, service or provider")


def min_and_max_present(versions: "VersionsSchema"):
    if versions.min is None and versions.min_strict is None:
        raise ValueError("min or min_strict should be present in versions of upgrade")

    if versions.max is None and versions.max_strict is None:
        raise ValueError("max or max_strict should be present in versions of upgrade")

    return versions


def min_less_than_max(versions: "VersionsSchema"):
    if versions.min is None or versions.max is None:
        return versions

    if compare_prototype_versions(str(versions.min), str(versions.max)) > 0:
        raise ValueError("Min version should be less or equal max version")

    return versions


def is_correct_pattern(pattern: str | None):
    if not isinstance(pattern, str):
        return pattern

    if not config.pattern.Pattern(pattern).is_valid:
        raise ValueError(f"Pattern is not valid regular expression: {pattern}")

    return pattern


def forbidden_mm_actions(actions: Any):
    if not isinstance(actions, dict):
        return None

    for name, data in actions.items():
        if name in ADCM_SERVICE_ACTION_NAMES_SET and ADCM_MM_ACTION_FORBIDDEN_PROPS_SET.intersection(data.keys()):
            raise ValueError(
                "Maintenance mode actions shouldn't have " f'"{ADCM_MM_ACTION_FORBIDDEN_PROPS_SET}" properties',
            )

    return actions


def patch_masking(value: dict | None) -> dict:
    # To make an action available, we can specify the making field without the value.
    # If a field is specified, but its value is None, we must set an explicit value that differs from the default,
    # so that after serialization this field remains and the code that patches the default values of the available
    # field will work.
    if value is None:
        return {}

    return value


def template_script_is_correct_path(value: Template, field_name: str) -> Template:
    if not is_path_correct(str(value.file.path)):
        raise ValueError(f'"{field_name}" has unsupported path format')

    return value
