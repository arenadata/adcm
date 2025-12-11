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

from core.legacy.job._repo import JobRepoI
from core.legacy.job.dto import LogCreateDTO, TaskCreateDTO, TaskUpdateMainFieldsDTO
from core.legacy.job.errors import TaskCreateError
from core.legacy.job.types import JobSpec
from core.types import ActionID, TaskID


@dataclass(slots=True)
class JobService:
    repo: JobRepoI

    def retrieve_scripts(self, action_id: ActionID) -> tuple[JobSpec, ...]:
        return self.repo.find_scripts_of_action(action_id=action_id)

    def create_task(self, payload: TaskCreateDTO) -> TaskID:
        return self.repo.create_task(payload=payload)

    def set_task_mapping_and_configuration(self, task_id: TaskID, payload: TaskUpdateMainFieldsDTO) -> None:
        self.repo.fill_task_mapping_and_configuration(task_id=task_id, payload=payload)

    def create_jobs(self, task_id: TaskID, scripts: tuple[JobSpec, ...] = ()) -> None:
        if not scripts:
            message = "Can't compose task for action, because no associated jobs found"
            raise TaskCreateError(message)

        self.repo.create_jobs(task_id=task_id, scripts=scripts)

        logs = []
        for job in self.repo.find_jobs_of_task(task_id=task_id):
            logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stdout", format="txt"))
            logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stderr", format="txt"))

        if logs:
            self.repo.create_logs(logs)
