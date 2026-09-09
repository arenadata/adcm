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

from core.action._types import JobSpec
from core.action.job._repo import JobRepoI, LogCreateDTO, TaskCreateDTO, TaskUpdateMainFieldsDTO
from core.action.job._termination import TerminationSignaller
from core.action.job.errors import JobTerminationError, JobValidationError, TaskCreateError
from core.action.job.operations import is_terminatable_status
from core.result import Fail
from core.types import ActionID, JobID, TaskID


@dataclass(slots=True)
class JobService:
    repo: JobRepoI
    signaller: TerminationSignaller

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

    def terminate_task(self, task_id: TaskID, *, force_allow_termination: bool = False) -> None:
        task = self.repo.get_task(task_id)

        if not (force_allow_termination or task.is_termination_allowed):
            message = f"Task #{task_id} termination is not allowed due to action definition"
            raise JobValidationError(message)

        if not is_terminatable_status(task.status):
            message = f"Task #{task_id} termination is not allowed due to status: {task.status.value}"
            raise JobValidationError(message)

        result = self.signaller.signal_termination_for_task(task)
        if isinstance(result, Fail):
            message = f"Task #{task_id} termination failed: {result.value}"
            raise JobTerminationError(message)

    def terminate_job(self, job_id: JobID) -> None:
        job = self.repo.get_job(job_id)

        if not job.is_termination_allowed:
            message = f"Job #{job_id} termination is not allowed due to action definition"
            raise JobValidationError(message)

        if not is_terminatable_status(job.status):
            message = f"Job #{job_id} termination is not allowed due to status: {job.status.value}"
            raise JobValidationError(message)

        result = self.signaller.signal_termination_for_job(job)
        if isinstance(result, Fail):
            message = f"Job #{job_id} termination failed: {result.value}"
            raise JobTerminationError(message)
