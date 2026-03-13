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
from enum import Enum

from pydantic import BaseModel


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LogFormat(str, Enum):
    TXT = "txt"
    JSON = "json"


@dataclass(slots=True)
class CheckLogResult:
    result: bool
    severity: Severity


@dataclass(slots=True)
class CheckLogContent:
    title: str
    type: str
    message: str
    result: bool
    severity: Severity


@dataclass(slots=True)
class GroupCheckLogContent(CheckLogContent):
    content: list[CheckLogContent]


####
# Ansible input types
####
class GroupCheckLogArguments(BaseModel):
    title: str
    success_msg: str = ""
    fail_msg: str = ""


class CheckLogArguments(BaseModel):
    title: str
    result: bool
    success_msg: str
    fail_msg: str
    severity: Severity = Severity.ERROR
    group: GroupCheckLogArguments | None = None
