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

from typing import TypeAlias, TypedDict

ConfigDict: TypeAlias = dict
AttrDict: TypeAlias = dict


class RelatedCHG(TypedDict):
    config_group_id: int
    config_id: int


class RelatedConfigs(TypedDict):
    object_id: int
    object_type: str
    prototype_id: int
    primary_config_id: int
    # field for storing related CHGs info (currently is out of scope)
    # config_host_groups: list[RelatedCHG]
