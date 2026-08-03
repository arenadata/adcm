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

# str is required for pydantic to correctly cast enum to value when calling `.dict`
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field


class ScriptType(str, Enum):
    ANSIBLE = "ansible"
    PYTHON = "python"
    INTERNAL = "internal"


class JobSpec(BaseModel):
    # basic info
    name: str
    display_name: str
    script: str
    script_type: ScriptType
    allow_to_terminate: bool

    # states
    state_on_fail: str
    multi_state_on_fail_set: list
    multi_state_on_fail_unset: list

    # extra
    params: dict


class ServiceManageConfigChange(BaseModel):
    key: str
    value: Any


class ServiceManageHostComponentChange(BaseModel):
    component: str
    hosts: list[str]


class ServiceManageServiceEntry(BaseModel):
    name: str
    config_changes: Annotated[list[ServiceManageConfigChange] | None, Field(default=None)]
    hc_changes: Annotated[list[ServiceManageHostComponentChange] | None, Field(default=None)]
