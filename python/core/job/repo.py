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

from typing import Collection, Iterable, Protocol

from core.job.dto import JobUpdateDTO, LogCreateDTO, TaskMutableFieldsDTO, TaskPayloadDTO, TaskUpdateDTO
from core.job.types import ActionInfo, Job, JobSpec, Task
from core.types import ActionID, ActionTargetDescriptor, CoreObjectDescriptor


class JobRepoInterface(Protocol):
    def get_task(self, id: int) -> Task:  # noqa: A002
        """Should raise `NotFoundError` on fail"""

    def create_task(
        self, target: ActionTargetDescriptor, owner: CoreObjectDescriptor, action: ActionInfo, payload: TaskPayloadDTO
    ) -> Task:
        ...

    def update_task(self, id: int, data: TaskUpdateDTO) -> None:  # noqa: A002
        ...

    def get_task_jobs(self, task_id: int) -> Iterable[Job]:
        ...

    def get_task_mutable_fields(self, id: int) -> TaskMutableFieldsDTO:  # noqa: A002
        ...

    def create_jobs(self, task_id: int, jobs: Iterable[JobSpec]) -> None:
        ...

    def get_job(self, id: int) -> Job:  # noqa: A002
        """Should raise `NotFoundError` on fail"""

    def update_job(self, id: int, data: JobUpdateDTO) -> None:  # noqa: A002
        ...

    def create_logs(self, logs: Iterable[LogCreateDTO]) -> None:
        ...

    def update_owner_state(self, owner: CoreObjectDescriptor, state: str) -> None:
        ...

    def update_owner_multi_states(
        self, owner: CoreObjectDescriptor, add_multi_states: Collection[str], remove_multi_states: Collection[str]
    ) -> None:
        ...


class ActionRepoInterface(Protocol):
    def get_action(self, id: ActionID) -> ActionInfo:  # noqa: A002
        ...

    def get_job_specs(self, id: ActionID) -> Iterable[JobSpec]:  # noqa: A002
        ...
