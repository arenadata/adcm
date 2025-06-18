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

import os
import time

from core.job.types import ExecutionStatus

from jobs.scheduler import repo, settings
from jobs.scheduler._types import CELERY_RUNNING_STATES, CeleryTaskState, TaskRunnerEnvironment, TaskShortInfo
from jobs.scheduler.logger import logger
from jobs.scheduler.utils import finalize_task, is_pid_exists, retrieve_celery_task_state


def _is_alive_local(task: TaskShortInfo) -> bool:
    worker_id = int(task.worker["worker_id"])
    if worker_id < 2:
        raise ValueError("Specify a valid PID (>=2)")

    return is_pid_exists(pid=worker_id)


def _is_alive_celery(task: TaskShortInfo) -> bool:
    celery_state = retrieve_celery_task_state(worker_id=task.worker["worker_id"])
    if celery_state == CeleryTaskState.ADCM_UNREACHABLE:
        logger.warning(f"Task #{task.id} can't check celery state. Considering dead.")
        return False

    return celery_state in CELERY_RUNNING_STATES


ALIVE_CHECKS_REGISTRY = {
    TaskRunnerEnvironment.LOCAL: _is_alive_local,
    TaskRunnerEnvironment.CELERY: _is_alive_celery,
}


def run_monitor_in_loop() -> None:
    scheduler_repo = repo
    logger.info(f"Monitor started (pid: {os.getpid()})")

    while True:
        time.sleep(settings.TASK_HEALTHCHECK_INTERVAL)
        try:
            for running_task in scheduler_repo.retrieve_running_tasks():
                if not running_task.worker or not ALIVE_CHECKS_REGISTRY[running_task.worker["environment"]](
                    task=running_task
                ):
                    finalize_task(task=running_task, status=ExecutionStatus.ABORTED)
        except Exception:  # noqa: BLE001
            logger.exception("Skipping monitor iteration due to exception:")
