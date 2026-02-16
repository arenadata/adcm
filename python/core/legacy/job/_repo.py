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

from typing import Iterable, Protocol

from core.legacy.job.dto import LogCreateDTO, TaskCreateDTO, TaskUpdateMainFieldsDTO
from core.legacy.job.types import Job, JobSpec
from core.types import ActionID, ActionTargetDescriptor, CoreObjectDescriptor, TaskID


class JobRepoI(Protocol):
    # retrieve

    def find_jobs_of_task(self, task_id: TaskID) -> tuple[Job, ...]:
        ...

    def find_scripts_of_action(self, action_id: ActionID) -> tuple[JobSpec, ...]:
        ...

    def find_action_owner(self, action_id: ActionID, target: ActionTargetDescriptor) -> CoreObjectDescriptor:
        ...

    # create

    def create_task(self, payload: TaskCreateDTO) -> TaskID:
        ...

    def create_jobs(self, task_id: TaskID, scripts: Iterable[JobSpec]) -> None:
        ...

    def create_logs(self, logs: Iterable[LogCreateDTO]) -> None:
        ...

    # update

    def fill_task_mapping_and_configuration(self, task_id: TaskID, payload: TaskUpdateMainFieldsDTO) -> None:
        ...
