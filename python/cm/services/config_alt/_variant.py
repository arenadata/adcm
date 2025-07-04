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

from typing import Callable, Iterable

from core.types import CoreObjectDescriptor

from cm.converters import core_type_to_model
from cm.services.config_alt._common import get_nested_config_value
from cm.services.config_alt.types import Configuration, VariantParameter
from cm.variant import get_builtin_variant


def resolve_variant(
    parameter: VariantParameter,
    retrieve_current_config: Callable[[], Configuration],
    owner: CoreObjectDescriptor,
) -> Iterable[str]:
    match parameter.source:
        case "config":
            source_param = parameter.payload["name"]
            choices = list(get_nested_config_value(config=retrieve_current_config().values, name=source_param))
        case "builtin":
            variant_func = parameter.payload["name"]
            func_args = parameter.payload.get("args")
            result = get_builtin_variant(
                obj=core_type_to_model(owner.type).objects.get(id=owner.id),
                func_name=variant_func,
                args=func_args,
            )
            if result is None:
                return []

            choices = list(result)
        case "inline":
            choices = list(parameter.payload["value"])
        case other:
            message = f"Variants of {other} aren't supported"
            raise ValueError(message)

    return choices
