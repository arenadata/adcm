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
from collections.abc import Collection, Iterable
from copy import deepcopy
from typing import NamedTuple
import copy
import json

from core.config import RelatedConfigs
from core.types import ADCMCoreType, ConfigID, CoreObjectDescriptor, ObjectConfigID, ObjectID

from cm.converters import core_type_to_model
from cm.errors import AdcmEx
from cm.models import Action, ConfigLog, Prototype, PrototypeConfig


class ConfigAttrPair(NamedTuple):
    config: dict
    attr: dict


def retrieve_config_attr_pairs(configurations: Iterable[ConfigID]) -> dict[ConfigID, ConfigAttrPair]:
    return {
        id_: ConfigAttrPair(config=config_ or {}, attr=attr_ or {})
        for id_, config_, attr_ in ConfigLog.objects.filter(id__in=configurations).values_list("id", "config", "attr")
    }


def retrieve_primary_configs(objects: dict[ADCMCoreType, set[ObjectID]]) -> list[RelatedConfigs]:
    configs = []

    for core_type, ids_set in objects.items():
        for object_id, prototype_id, current_config in (
            core_type_to_model(core_type)
            .objects.filter(id__in=ids_set)
            .values_list("id", "prototype_id", "config__current")
        ):
            if not current_config:
                continue
            configs.append(
                RelatedConfigs(
                    object_id=object_id,
                    object_type=core_type.value,
                    prototype_id=prototype_id,
                    primary_config_id=current_config,
                )
            )

    return configs


def retrieve_configs_with_revision(objects: dict[ADCMCoreType, set[ObjectID]]) -> dict[CoreObjectDescriptor, ConfigID]:
    objconfig_obj_map: dict[ObjectConfigID, CoreObjectDescriptor] = {}
    for core_type, ids in objects.items():
        for object_id, objectconfig_id in (
            core_type_to_model(core_type).objects.filter(id__in=ids).values_list("id", "config_id")
        ):
            if not objectconfig_id:
                continue
            objconfig_obj_map[objectconfig_id] = CoreObjectDescriptor(id=object_id, type=core_type)

    configs_with_revision: dict[CoreObjectDescriptor, ConfigID] = {}
    configlogs_qs = ConfigLog.objects.filter(
        obj_ref_id__in=objconfig_obj_map, configrevision__isnull=False
    ).values_list("id", "obj_ref_id")
    for config_id, objectconfig_id in configlogs_qs:
        cod = objconfig_obj_map.get(objectconfig_id)
        if not cod:
            continue
        configs_with_revision[cod] = config_id

    return configs_with_revision


def convert_attr_to_adcm_meta(attr: dict) -> dict:
    attr = deepcopy(attr)
    adcm_meta = defaultdict(dict)
    attr.pop("custom_group_keys", None)
    group_keys = attr.pop("group_keys", {})

    for key, value in attr.items():
        adcm_meta[f"/{key}"].update({"isActive": value["active"]})

    for key, value in group_keys.items():
        if isinstance(value, dict):
            if isinstance(value["value"], bool):
                adcm_meta[f"/{key}"].update({"isSynchronized": not value["value"]})
            for sub_key, sub_value in value["fields"].items():
                adcm_meta[f"/{key}/{sub_key}"].update({"isSynchronized": not sub_value})
        else:
            adcm_meta[f"/{key}"].update({"isSynchronized": not value})

    return adcm_meta


def convert_adcm_meta_to_attr(adcm_meta: dict) -> dict:
    attr = defaultdict(dict)
    try:
        for key, value in adcm_meta.items():
            _, key, *sub_key = key.split("/")

            if sub_key:
                sub_key = sub_key[0]

                if key not in attr["group_keys"]:
                    attr["group_keys"].update({key: {"value": None, "fields": {}}})

                attr["group_keys"][key]["fields"].update({sub_key: not value["isSynchronized"]})
            else:
                if "isSynchronized" in value and "isActive" in value:
                    # activatable group in config-group
                    attr[key].update({"active": value["isActive"]})
                    attr["group_keys"].update({key: {"value": not value["isSynchronized"], "fields": {}}})
                elif "isActive" in value:
                    # activatable group not in config-group
                    attr[key].update({"active": value["isActive"]})
                else:
                    # non-group root field in config-group
                    attr["group_keys"].update({key: not value["isSynchronized"]})
    except (KeyError, ValueError):
        return adcm_meta

    return attr


def represent_json_type_as_string(prototype: Prototype, value: dict, action_: Action | None = None) -> dict:
    value = copy.deepcopy(value)

    for name, sub_name in PrototypeConfig.objects.filter(prototype=prototype, type="json", action=action_).values_list(
        "name", "subname"
    ):
        if name not in value or (sub_name and sub_name not in value[name]):
            continue

        if sub_name:
            new_value = json.dumps(value[name][sub_name]) if value[name][sub_name] is not None else None
            value[name][sub_name] = new_value
        else:
            new_value = json.dumps(value[name]) if value[name] is not None else None
            value[name] = new_value

    return value


def represent_string_as_json_type(prototype_configs: Collection[PrototypeConfig], value: dict) -> dict:
    value = copy.deepcopy(value)

    for prototype_config in prototype_configs:
        name = prototype_config.name
        sub_name = prototype_config.subname

        # json may be `null`/`None` if it's not required, so we patch it as () to skip this field
        if name not in value or sub_name not in (value[name] or ()):
            continue

        try:
            if sub_name:
                new_value = json.loads(value[name][sub_name]) if value[name][sub_name] is not None else None
                value[name][sub_name] = new_value
            else:
                new_value = json.loads(value[name]) if value[name] is not None else None
                value[name] = new_value
        except json.JSONDecodeError:
            raise AdcmEx(
                code="CONFIG_KEY_ERROR",
                msg=f"The '{name}/{sub_name}' key must be in the json format.",
            ) from None
        except TypeError:
            raise AdcmEx(
                code="CONFIG_KEY_ERROR",
                msg=f"The '{name}/{sub_name}' key must be a string type.",
            ) from None

    return value
