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

from cm.models import TaskLog
from cm.transition.action import RetrieveStartImpossibleReason
from core.action import ExecutionStatus, TaskRunnerEnvironment, WorkerInfo
from core.action.job import JobRepoI
from core.action.scheduler import TaskQueuer
from core.legacy.job.runners import JobFilterPredicate, TaskRunner, always_true
from core.scenarios.concern import ConcernScenarios
from core.types import TaskID
from jobs.scheduler import repo as scheduler_repo_module
from use_cases.job.scheduler import queue_task, schedule_task
import dishka

# no real process is started in tests, so there's no pid to remember
_NO_WORKER_ID = 0


class TestTaskQueuer(TaskQueuer):
    """
    Records a worker like the local queuer does, but starts no process:
    task execution is performed in-place by `TaskFlow.execute_task`.
    """

    env = TaskRunnerEnvironment.LOCAL

    def queue(self, task_id: TaskID) -> WorkerInfo:
        _ = task_id

        return WorkerInfo(environment=self.env, worker_id=_NO_WORKER_ID)


@dataclass(slots=True)
class TaskFlow:
    """
    Imitates what scheduler and separate task runner process do for one known task.

    Production-close parts are called as is: validation, concern distribution and status transitions
    are the very same functions launcher calls.
    Skipped are the parts that make no sense for tests: claiming (locking) records
    and starting a separate process for a task.
    """

    container: dishka.Container

    def launch_task(self, task_id: TaskID) -> None:
        """Performs all steps left for a task to be executed, picking them by current status"""

        status = ExecutionStatus(TaskLog.objects.values_list("status", flat=True).get(id=task_id))

        match status:
            case ExecutionStatus.CREATED:
                self.schedule_task(task_id=task_id)
                self.queue_task(task_id=task_id)

            case ExecutionStatus.SCHEDULED:
                self.queue_task(task_id=task_id)

            case ExecutionStatus.QUEUED:
                pass

            case _:
                message = f"Task #{task_id} can't be launched from status {status.value}"
                raise RuntimeError(message)

        self.execute_task(task_id=task_id)

    def schedule_task(self, task_id: TaskID) -> None:
        """
        `CREATED` -> `SCHEDULED`: performs validation and distributes concerns.

        Note that validation failures aren't raised: task is set to `REVOKED` instead
        (see `assert_task_revoked`).
        """

        schedule_task(
            task_id=task_id,
            env_type=TaskRunnerEnvironment.LOCAL,
            job_repo=self.container.get(JobRepoI),
            scheduler_repo=scheduler_repo_module.SchedulerRepo(scheduler_repo_module),
            retrieve_sir=self.container.get(RetrieveStartImpossibleReason),
            concern_scenarios=self.container.get(ConcernScenarios),
        )

    def queue_task(self, task_id: TaskID) -> None:
        """`SCHEDULED` -> `QUEUED`: records worker without starting one"""

        queue_task(queuer=TestTaskQueuer(), task_id=task_id, job_repo=self.container.get(JobRepoI))

    def execute_task(self, task_id: TaskID) -> None:
        """Performs what `task_runner.py` does for a task, but in current process"""

        with self.container(context={JobFilterPredicate: always_true}):
            runner = self.container.get(TaskRunner)
            runner.run(task_id=task_id)


class TaskFlowMixin:
    """
    Gives access to `TaskFlow` for test cases.

    Expects `container` to be available, like it is in base test suites.
    Pass another one to run a task with overridden dependencies.
    """

    container: dishka.Container

    def task_runner(self, container: dishka.Container | None = None) -> TaskFlow:
        return TaskFlow(container=container if container is not None else self.container)
