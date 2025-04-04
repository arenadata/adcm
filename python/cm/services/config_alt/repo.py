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

from core.types import CoreObjectDescriptor, ObjectID

from cm.converters import core_type_to_model
from cm.models import ConfigHostGroup, ConfigLog, Prototype, PrototypeConfig
from cm.services.config_alt.types import (
    Attributes,
    Configuration,
    ParameterFullName,
    ensure_full_name,
    level_names_to_full_name,
)


def get_prototype_group_customization_flag(prototype_id: int) -> bool:
    return Prototype.objects.values_list("config_group_customization", flat=True).get(id=prototype_id)


def retrieve_object_config_prototypes(prototype_id: int):
    return PrototypeConfig.objects.filter(prototype_id=prototype_id, action=None).order_by("id")


# config


def get_object_configuration(owner: CoreObjectDescriptor) -> Configuration:
    config_log = ConfigLog.objects.get(
        id=core_type_to_model(owner.type).objects.values_list("config__current", flat=True).filter(id=owner.id).first()
    )
    return _record_to_configuration(config_log, include_sync_attrs=False)


def get_host_group_configuration(group_id: ObjectID) -> Configuration:
    config_log = ConfigLog.objects.get(
        id=ConfigHostGroup.objects.values_list("config__current", flat=True).filter(id=group_id).first()
    )
    return _record_to_configuration(config_log, include_sync_attrs=True)


def _record_to_configuration(record: ConfigLog, *, include_sync_attrs: bool = False) -> Configuration:
    convert_attrs = _convert_group_db_format_to_attributes if include_sync_attrs else _convert_db_format_to_attributes
    return Configuration(values=record.config, attributes=convert_attrs(record.attr), description=record.description)


def _convert_db_format_to_attributes(attrs: dict[str, dict]) -> dict[ParameterFullName, Attributes]:
    return {
        ensure_full_name(group_name): Attributes(is_active=attr["active"])
        for group_name, attr in attrs.items()
        if group_name not in ("group_keys", "custom_group_keys")
    }


def _convert_group_db_format_to_attributes(attrs: dict[str, dict]) -> dict[ParameterFullName, Attributes]:
    result = {}

    group_config = attrs["group_keys"]

    for name, first_level in group_config.items():
        full_name = ensure_full_name(name)
        if isinstance(first_level, bool):
            result[full_name] = Attributes(is_synced=not first_level)
            continue

        # it's group and it may or may not be active
        # if it's not an active group, then "value" will be None
        # and it's important for further attrs detection
        v1_synced_value = first_level["value"]
        if v1_synced_value is not None:
            result[full_name] = Attributes(is_active=attrs.get(name, {}).get("active"), is_synced=not v1_synced_value)

        for field_name, sync_value in first_level["fields"].items():
            nested_full_name = level_names_to_full_name((full_name, field_name))
            result[nested_full_name] = Attributes(is_synced=not sync_value)

    return result
