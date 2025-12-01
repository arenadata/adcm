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

from core.config._names import level_names_to_full_name
from core.config._spec import FullSpec
from core.config._spec.parameters import (
    ExtraProperties,
    Identifier,
    ParameterGroup,
    ReadOnlyRule,
    Selection,
    StringParameter,
)
from core.config._types import Defaults


def id_(*levels: str) -> Identifier:
    full = level_names_to_full_name(levels)
    return Identifier(full=full, name=levels[-1])


def build() -> tuple[FullSpec, Defaults]:
    spec = FullSpec.from_parameters(
        ParameterGroup(
            identifier=id_("sg"),
            extra=ExtraProperties(edit_rule=ReadOnlyRule(read_only="any")),
            selection=Selection(is_required=True),
        ),
        ParameterGroup(identifier=id_("sg", "g")),
        StringParameter(identifier=id_("sg", "g", "v")),
    )

    defaults = Defaults(selection={"/sg": "g"})

    return spec, defaults
