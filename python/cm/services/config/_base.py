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

from core.types import ConfigID

from cm.models import ConfigLog


class ConfigAttrPair(NamedTuple):
    config: dict
    attr: dict


def retrieve_config_attr_pairs(configurations: Iterable[ConfigID]) -> dict[ConfigID, ConfigAttrPair]:
    return {
        id_: ConfigAttrPair(config=config_ or {}, attr=attr_ or {})
        for id_, config_, attr_ in ConfigLog.objects.filter(id__in=configurations).values_list("id", "config", "attr")
    }
