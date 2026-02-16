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

from collections import defaultdict
from typing import Generator

import core

_IS_ACTIVE = "isActive"
_IS_SYNCED = "isSynchronized"


def convert_adcm_meta_to_attr(adcm_meta: dict[core.config.ParameterFullName, dict]) -> dict:
    activation = {}
    group_keys = _recursive_defaultdict_on_fields()

    for name, attrs in adcm_meta.items():
        if _IS_ACTIVE in attrs:
            activation[name.lstrip("/")] = {"active": attrs[_IS_ACTIVE]}

        if _IS_SYNCED not in attrs:
            continue

        *groups, own_name = core.config.names.full_name_to_level_names(name)

        target_node = group_keys

        for group in groups:
            if group not in target_node:
                # "child" came before group
                target_node[group] = {"fields": {}, "value": None}
            elif isinstance(target_node[group], bool):
                # mean previously considered value is actually a group
                target_node[group] = {"fields": {}, "value": target_node[group]}

            target_node = target_node[group]["fields"]

        value_to_set = not attrs[_IS_SYNCED]
        if own_name not in target_node:
            target_node[own_name] = value_to_set
        else:
            target_node[own_name]["value"] = value_to_set

    if not group_keys:
        return activation

    return activation | {"group_keys": group_keys}


def convert_attr_to_adcm_meta(attr: dict) -> dict:
    result = {
        core.config.names.ensure_full_name(key): {_IS_ACTIVE: node["active"]}
        for key, node in attr.items()
        if key not in ("group_keys", "custom_group_keys")
    }

    group_keys = attr.get("group_keys")
    if not group_keys:
        return result

    for name, group_keys_value in _extract_sync_values(group_keys):
        value_to_set = not group_keys_value

        if name in result:
            result[name][_IS_SYNCED] = value_to_set
        else:
            result[name] = {_IS_SYNCED: value_to_set}

    return result


def _extract_sync_values(
    node: dict, group: tuple[core.config.ParameterLevelName, ...] = ()
) -> Generator[tuple[core.config.ParameterFullName, bool], None, None]:
    for key, value in node.items():
        node_keys = (*group, key)
        if isinstance(value, bool):
            name = core.config.names.level_names_to_full_name(node_keys)
            yield name, value
        elif isinstance(value, dict):
            group_value = value.get("value")
            if isinstance(group_value, bool):
                name = core.config.names.level_names_to_full_name(node_keys)
                yield name, group_value

            child_fields = value.get("fields", {})
            if isinstance(child_fields, dict):
                yield from _extract_sync_values(node=child_fields, group=node_keys)


def _recursive_defaultdict_on_fields() -> defaultdict:
    return defaultdict(lambda: {"fields": _recursive_defaultdict_on_fields(), "value": None})
