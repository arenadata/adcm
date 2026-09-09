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

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
import os
import errno
import logging

from cm.legacy.services.job.run import run_task_in_local_subprocess
from core.action import JobShortInfo, TaskRunnerEnvironment, TaskShortInfo, WorkerInfo
from core.action.job import ExecutorTerminator, TaskRunnerTerminator
from core.action.scheduler import LivenessReport, TaskLivenessStatus, TaskMonitor, TaskQueuer, Terminator
from core.types import PID, TaskID
from jobs.scheduler import repo

monitor_logger = logging.getLogger("scheduler.monitor")

# Implementations


@dataclass(slots=True)
class LocalTerminator(Terminator):
    task_runner_terminator: TaskRunnerTerminator
    executor_terminator: ExecutorTerminator

    def terminate_task(self, task: TaskShortInfo) -> None:
        self.task_runner_terminator.terminate(int(task.worker["worker_id"]))

    def terminate_job(self, job: JobShortInfo) -> None:
        self.executor_terminator.terminate(int(job.worker["worker_id"]))


@dataclass(slots=True)
class LocalTaskMonitor(TaskMonitor):
    def analyze_liveness(self, tasks: Iterable[TaskShortInfo]) -> LivenessReport:
        result = defaultdict(list)

        for task in tasks:
            liveness_status = self.is_alive(task)
            result[liveness_status].append(task)

        monitor_logger.debug("Liveness check result: %s", result)

        return result

    def is_alive(self, task: TaskShortInfo) -> TaskLivenessStatus:
        try:
            pid = int(task.worker["worker_id"])
        except ValueError:
            return TaskLivenessStatus.UNKNOWN

        if pid < 2:
            return TaskLivenessStatus.UNKNOWN

        if is_pid_exists(pid=pid):
            return TaskLivenessStatus.ALIVE

        return TaskLivenessStatus.DEAD


class LocalTaskQueuer(TaskQueuer):
    env = TaskRunnerEnvironment.LOCAL
    repo = repo

    def queue(self, task_id: TaskID) -> WorkerInfo:
        pid = run_task_in_local_subprocess(task=self.repo.retrieve_task_orm(task_id=task_id), command="start")

        return WorkerInfo(environment=self.env, worker_id=pid)


# Common functions


def is_pid_exists(pid: PID) -> bool:
    """
    Sends a special signal `0` to `pid`.
    `0` signal is not sends an actual signal, but performs error checking.
    Possible errors are: EINVAL (invalid signal), EPERM (no permissions), ESRCH (no process)
        Source: man 2 kill
    """

    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:  # No such process
            return False

        elif err.errno == errno.EPERM:  # Permission error, process exists
            return True

        raise

    return True
