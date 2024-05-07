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

from collections import OrderedDict, defaultdict
from typing import Any, Iterable, NamedTuple, TypeAlias

from core.types import PrototypeID
from typing_extensions import Self

from cm.models import PrototypeConfig


class ConfigParamPlainSpec(NamedTuple):
    type: str
    display_name: str
    description: str

    default: str
    limits: dict
    ui_options: dict
    required: bool

    group_customization: bool | None

    @classmethod
    def get_fields(cls) -> tuple[str, ...]:
        return cls._fields

    @classmethod
    def from_dict(cls, value: dict) -> Self:
        return cls(**{key: val for key, val in value.items() if key in cls._fields})


# key in format "{root_param_name}/{child_param_name}"
# for elements in root and groups it'll be "{param_name}/"
ConfigParamCompositeKey: TypeAlias = str
FlatSpec: TypeAlias = OrderedDict[ConfigParamCompositeKey, ConfigParamPlainSpec]


def retrieve_flat_spec_for_objects(prototypes: Iterable[PrototypeID]) -> dict[PrototypeID, FlatSpec]:
    flat_config_specification = defaultdict(OrderedDict)

    for row in _filter_configs(prototype_id__in=prototypes, action=None):
        flat_config_specification[row["prototype_id"]][
            f"{row['name']}/{row['subname']}"
        ] = ConfigParamPlainSpec.from_dict(row)

    return flat_config_specification


def convert_to_flat_spec_from_proto_flat_spec(
    prototypes_flat_spec: dict[ConfigParamCompositeKey, PrototypeConfig],
) -> FlatSpec:
    flat_config_specification = OrderedDict()

    for key, config_proto in prototypes_flat_spec.items():
        flat_config_specification[key] = ConfigParamPlainSpec(
            type=config_proto.type,
            display_name=config_proto.display_name,
            description=config_proto.description or "",
            default=str(config_proto.default or ""),
            limits=config_proto.limits or {},
            ui_options=config_proto.ui_options or {},
            required=config_proto.required,
            group_customization=config_proto.group_customization,
        )

    return flat_config_specification


def _filter_configs(**filters: Any) -> Iterable[dict]:
    return (
        PrototypeConfig.objects.filter(**filters)
        .values("prototype_id", "name", "subname", *ConfigParamPlainSpec.get_fields())
        .order_by("id")
    )
