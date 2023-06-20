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
    top_fields = PrototypeConfig.objects.filter(prototype=parent_object.prototype, action=action, subname="").order_by(
        "id"
    )

    for field in top_fields:
        item = get_item_schema(field=field, parent_object=parent_object)

        if field.type == "group":
            child_fields = (
                PrototypeConfig.objects.filter(prototype=parent_object.prototype, action=action, name=field.name)
                .exclude(type="group")
                .order_by("id")
            )

            for child_field in child_fields:
                item["children"].append(get_item_schema(field=child_field, parent_object=parent_object))

        schema.append(item)

    return schema
