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
from datetime import datetime

from pydantic import BaseModel

from core.job.types import ExecutionStatus


class TaskUpdateDTO(BaseModel):
    pid: int | None = None
    start_date: datetime | None = None
    finish_date: datetime | None = None
    status: ExecutionStatus | None = None


class JobUpdateDTO(BaseModel):
    pid: int | None = None
    start_date: datetime | None = None
    finish_date: datetime | None = None
    status: ExecutionStatus | None = None


class LogCreateDTO(BaseModel):
    job_id: int
    name: str
    type: str
    format: str


class TaskPayloadDTO(BaseModel):
    verbose: bool = False

    conf: dict | None = None
    attr: dict | None = None

    hostcomponent: list[dict] | None = None
    post_upgrade_hostcomponent: list[dict] | None = None
