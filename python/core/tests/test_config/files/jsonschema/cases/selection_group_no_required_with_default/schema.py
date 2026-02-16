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
from core.config._spec.parameters import Identifier, ParameterGroup, Selection, StringParameter
from core.config._types import Defaults


def id_(*levels: str) -> Identifier:
    full = level_names_to_full_name(levels)
    return Identifier(full=full, name=levels[-1])


def build() -> tuple[FullSpec, Defaults]:
    spec = FullSpec.from_parameters(
        ParameterGroup(identifier=id_("sg"), selection=Selection(is_required=False)),
        ParameterGroup(identifier=id_("sg", "nondef")),
        StringParameter(identifier=id_("sg", "nondef", "with_default")),
        ParameterGroup(identifier=id_("sg", "df")),
        StringParameter(identifier=id_("sg", "df", "with_default")),
        StringParameter(identifier=id_("sg", "df", "no_default")),
        ParameterGroup(identifier=id_("sg", "a")),
        StringParameter(identifier=id_("sg", "a", "no_default")),
    )

    defaults = Defaults(
        values={
            "/sg/nondef/with_default": "sg-nondef-val",
            "/sg/df/with_default": "sg-df-val",
        },
        selection={"/sg": "df"},
    )

    return spec, defaults
