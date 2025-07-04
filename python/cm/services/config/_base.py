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

from typing import Iterable, NamedTuple

from core.types import ADCMCoreType, ConfigID, CoreObjectDescriptor, ObjectConfigID, ObjectID

from cm.converters import core_type_to_model
from cm.models import ConfigLog
from cm.services.config.types import RelatedConfigs


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
