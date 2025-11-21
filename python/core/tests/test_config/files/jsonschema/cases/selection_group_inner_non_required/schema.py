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
        ParameterGroup(identifier=id_("sg"), selection=Selection(is_required=False, use_as_default=None)),
        ParameterGroup(identifier=id_("sg", "g1")),
        StringParameter(identifier=id_("sg", "g1", "with_default"), is_required=False),
        StringParameter(identifier=id_("sg", "g1", "without_default"), is_required=False),
        ParameterGroup(identifier=id_("sg", "g2")),
        StringParameter(identifier=id_("sg", "g2", "without_default"), is_required=False),
        StringParameter(identifier=id_("sg", "g2", "with_default"), is_required=False),
    )

    defaults = {
        "/sg/g1/with_default": "3",
        "/sg/g1/without_default": None,
        "/sg/g2/with_default": "8",
        "/sg/g2/without_default": None,
    }

    return spec, defaults
