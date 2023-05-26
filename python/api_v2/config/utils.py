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


def get_schema(parent_object: ADCMEntity, action: Action | None = None):
    data = []

    for config_prototype in PrototypeConfig.objects.filter(prototype=parent_object.prototype, action=action).order_by(
        "id"
    ):
        item = {
            "name": config_prototype.subname if config_prototype.subname else config_prototype.name,
            "displayName": config_prototype.display_name,
            "type": config_prototype.type,
            "default": get_default(conf=config_prototype, prototype=parent_object.prototype),
            "isReadOnly": config_is_ro(
                obj=parent_object,
                key=f"{config_prototype.name}/{config_prototype.subname}",
                limits=config_prototype.limits,
            ),
            "isActive": group_is_activatable(spec=config_prototype),
            "validation": {
                "isRequired": config_prototype.required,
                "minValue": config_prototype.limits.get("min"),
                "maxValue": config_prototype.limits.get("max"),
            },
            "options": [{"label": k, "value": v} for k, v in config_prototype.limits.get("option", {}).items()],
        }

        if config_prototype.type == "group":
            item["child"] = list(
                PrototypeConfig.objects.filter(
                    prototype=parent_object.prototype, action=action, name=config_prototype.name
                )
                .exclude(type="group")
                .order_by("id")
                .values_list("subname", flat=True)
            )
        else:
            item["child"] = []

        data.append(item)

    return data
