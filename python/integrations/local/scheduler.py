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
from pathlib import Path
import os
import errno
import logging
import subprocess

from cm.legacy.utils import get_env_with_venv_path
from core.action import JobShortInfo, TaskRunnerEnvironment, TaskShortInfo, WorkerInfo
from core.action.job import ExecutorTerminator, JobRepoI, TaskRunnerTerminator, TaskShortFilter
from core.action.scheduler import (
    LivenessReport,
    ProcessStarter,
    TaskLivenessStatus,
    TaskMonitor,
    TaskQueuer,
    Terminator,
)
from core.settings import Directories
from core.types import PID, TaskID

monitor_logger = logging.getLogger("scheduler.monitor")
process_logger = logging.getLogger("adcm")

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


@dataclass(slots=True)
class LocalProcessStarter(ProcessStarter):
    def start(self, task_id: TaskID, venv: str, code_dir: Path, log_dir: Path) -> PID:
        err_file = open(  # noqa: SIM115
            Path(log_dir, "task_runner.err"), "a+", encoding="utf-8"
        )

        cmd = [
            str(code_dir / "task_runner.py"),
            "start",
            str(task_id),
        ]
        process_logger.debug("Task #%d run cmd: %s", task_id, " ".join(cmd))
        proc = subprocess.Popen(  # noqa: SIM115
            args=cmd, stderr=err_file, env=get_env_with_venv_path(venv=venv)
        )

        return proc.pid


@dataclass(slots=True)
class LocalTaskQueuer(TaskQueuer):
    job_repo: JobRepoI
    directories: Directories
    process_starter: ProcessStarter

    env = TaskRunnerEnvironment.LOCAL

    def queue(self, task_id: TaskID) -> WorkerInfo:
        task = next(iter(self.job_repo.find_tasks_short(TaskShortFilter(ids=[task_id]))))
        pid = self.process_starter.start(
            task_id=task_id, venv=task.action.venv, code_dir=self.directories.code, log_dir=self.directories.logs
        )

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
