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
from copy import deepcopy

from cm.adcm_config.config import config_is_ro, get_default, group_is_activatable
from cm.models import Action, ADCMEntity, PrototypeConfig


def get_item_schema(field: PrototypeConfig, parent_object: ADCMEntity) -> dict:
    item = {
        "name": field.subname if field.subname else field.name,
        "displayName": field.display_name,
        "type": field.type,
        "default": get_default(conf=field, prototype=parent_object.prototype),
        "isReadOnly": config_is_ro(
            obj=parent_object,
            key=f"{field.name}/{field.subname}",
            limits=field.limits,
        ),
        "isActive": group_is_activatable(spec=field),
        "validation": {
            "isRequired": field.required,
            "minValue": field.limits.get("min"),
            "maxValue": field.limits.get("max"),
        },
        "options": [{"label": k, "value": v} for k, v in field.limits.get("option", {}).items()],
        "children": [],
    }

    return item


def get_config_schema(parent_object: ADCMEntity, action: Action | None = None) -> list:
    schema = []

    if action:
        # if action is provided, it's enough to find config prototypes
        # and for upgrade's actions it is important to not operate with parent object,
        # because action is from bundle, not "created object" like cluster/provider
        config_prototypes = PrototypeConfig.objects.filter(action=action)
    else:
        config_prototypes = PrototypeConfig.objects.filter(prototype=parent_object.prototype, action=action)

    top_fields = config_prototypes.filter(subname="").order_by("id")

    for field in top_fields:
        item = get_item_schema(field=field, parent_object=parent_object)

        if field.type == "group":
            child_fields = config_prototypes.filter(name=field.name).exclude(type="group").order_by("id")

            for child_field in child_fields:
                item["children"].append(get_item_schema(field=child_field, parent_object=parent_object))

        schema.append(item)

    return schema


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
                adcm_meta[f"/{key}"].update({"isSynchronized": value["value"]})
            for sub_key, sub_value in value["fields"].items():
                adcm_meta[f"/{key}/{sub_key}"].update({"isSynchronized": sub_value})
        else:
            adcm_meta[f"/{key}"].update({"isSynchronized": value})

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

                attr["group_keys"][key]["fields"].update({sub_key: value["isSynchronized"]})
            else:
                if "isSynchronized" in value and "isActive" in value:
                    # activatable group in config-group
                    attr[key].update({"active": value["isActive"]})
                    attr["group_keys"].update({key: {"value": value["isSynchronized"], "fields": {}}})
                elif "isActive" in value:
                    # activatable group not in config-group
                    attr[key].update({"active": value["isActive"]})
                else:
                    # non-group root field in config-group
                    attr["group_keys"].update({key: value["isSynchronized"]})
    except (KeyError, ValueError):
        return adcm_meta

    return attr
