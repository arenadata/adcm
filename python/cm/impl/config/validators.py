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
from typing import Any

from core import config
from core.types import CoreObjectDescriptor

from cm.converters import core_type_to_model
from cm.legacy.variant import get_builtin_variant


class DefaultsVariantResolver(config.VariantValidator):
    __slots__ = ()

    def is_value_allowed(self, value: Any, parameter: config.spec.p.VariantParameter) -> bool:
        if parameter.source != "inline":
            return True

        return value in parameter.payload["value"]


@dataclass(slots=True)
class MainConfigVariantResolver(config.MainConfigVariantResolver):
    owner: CoreObjectDescriptor
    reference_config: config.Configuration

    def resolve(self, parameter: config.spec.p.VariantParameter) -> tuple:
        match parameter.source:
            case "config":
                source_param = config.names.ensure_full_name(parameter.payload["name"])
                values = config.get_by_full_name(values=self.reference_config.values, name=source_param)
                choices = tuple(values)
            case "builtin":
                variant_func = parameter.payload["name"]
                func_args = parameter.payload.get("args")
                obj = core_type_to_model(self.owner.type).objects.get(id=self.owner.id)
                result = get_builtin_variant(obj=obj, func_name=variant_func, args=func_args)
                choices = tuple(result or ())
            case "inline":
                choices = tuple(parameter.payload["value"])

        return choices

    def is_value_allowed(self, value: Any, parameter: config.spec.p.VariantParameter) -> bool:
        choices = self.resolve(parameter)
        return value in choices
