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

from cm.services.job.run import run_task_in_local_subprocess
from core.types import TaskID
from jobs.scheduler import repo as SchedulerRepo  # noqa: N812
from jobs.scheduler._types import TaskQueuer, TaskRunnerEnvironment, WorkerInfo
from jobs.worker.tasks import run_task

# TODO: restart


class LocalTaskQueuer(TaskQueuer):
    env = TaskRunnerEnvironment.LOCAL
    scheduler_repo = SchedulerRepo

    def queue(self, task_id: TaskID) -> WorkerInfo:
        pid = run_task_in_local_subprocess(task=self.scheduler_repo.retrieve_task_orm(task_id=task_id), command="start")

        return WorkerInfo(environment=self.env.value, worker_id=pid)


class CeleryTaskQueuer(TaskQueuer):
    env = TaskRunnerEnvironment.CELERY

    def queue(self, task_id: TaskID) -> WorkerInfo:
        result = run_task.delay(task_id=task_id)  # pyright: ignore [reportFunctionMemberAccess]

        return WorkerInfo(environment=self.env.value, worker_id=result.id)
