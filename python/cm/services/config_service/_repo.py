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

from core.types import CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from django.db.models import F

from cm import converters
from cm.models import ConfigHostGroup, ConfigLog, PrototypeConfig


@dataclass(slots=True)
class ConfigPrototypeInfo:
    bundle_hash: str
    group_customization_flag: bool
    parameter_prototypes: tuple[PrototypeConfig, ...]


@dataclass(slots=True)
class HostGroupConfigRecord:
    group_id: int
    values: dict
    attrs: dict


def get_config_prototype_info(owner: CoreObjectDescriptor) -> ConfigPrototypeInfo:
    model = converters.core_type_to_model(owner.type)
    response = model.objects.values(
        "prototype_id",
        customization=F("prototype__config_group_customization"),
        bundle_hash=F("prototype__bundle__hash"),
    ).get(id=owner.id)
    parameter_prototypes = tuple(
        PrototypeConfig.objects.filter(prototype_id=response["prototype_id"], action_id=None).order_by("pk")
    )

    return ConfigPrototypeInfo(
        bundle_hash=response["bundle_hash"],
        group_customization_flag=response["customization"],
        parameter_prototypes=parameter_prototypes,
    )


def get_configurations_of_host_groups(owner: CoreObjectDescriptor) -> tuple[HostGroupConfigRecord, ...]:
    model = converters.core_type_to_model(owner.type)
    content_type = ContentType.objects.get_for_model(model)

    group_config_id_query = ConfigHostGroup.objects.filter(object_id=owner.id, object_type=content_type).values_list(
        "id", "config__current"
    )
    group_config_id_map: dict[int, int] = dict(group_config_id_query)

    configs_query = ConfigLog.objects.filter(id__in=group_config_id_map.values())
    configs = {config.pk: (config.config, config.attr) for config in configs_query}

    records = ((group_id, *configs[config_id]) for group_id, config_id in group_config_id_map.items())
    return tuple(HostGroupConfigRecord(*rec) for rec in records)
