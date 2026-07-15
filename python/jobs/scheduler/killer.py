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

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
import os
import time
import signal

from core.action import ExecutionStatus
from core.action.job import JobRepoI
from django.db.transaction import atomic
import dishka

from jobs.scheduler._types import JobShortInfo, TaskRunnerEnvironment, TaskShortInfo
from jobs.scheduler.logger import logger
from jobs.scheduler.repo import (
    get_planned_for_termination,
    lock_job_for_termination,
    lock_task_for_termination,
    retrieve_job,
    retrieve_task,
)
from jobs.scheduler.utils import UTC


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(slots=True)
class Clock:
    period: timedelta

    next_tick_after: datetime = datetime.min.replace(tzinfo=UTC)

    sleep: Callable[[float], None] = time.sleep
    now: Callable[[], datetime] = utc_now

    def sleep_until_next_tick(self) -> None:
        now = self.now()

        until_next_tick = (self.next_tick_after - now).total_seconds()
        if until_next_tick > 0:
            self.sleep(until_next_tick)

        self.next_tick_after = now + self.period


TASK_KILLER_REGISTRY: dict[TaskRunnerEnvironment, Callable[[TaskShortInfo], Any]] = {
    TaskRunnerEnvironment.LOCAL: lambda x: os.kill(int(x.worker["worker_id"]), signal.SIGTERM),
}

JOB_KILLER_REGISTRY: dict[TaskRunnerEnvironment, Callable[[JobShortInfo], Any]] = {
    TaskRunnerEnvironment.LOCAL: lambda x: os.kill(int(x.worker["worker_id"]), signal.SIGTERM),
}


def run_killer_in_loop(container: dishka.Container) -> None:
    logger.info("Job killer started (pid: %s)", os.getpid())

    repo: JobRepoI = container.get(JobRepoI)

    from jobs.scheduler import settings

    clock = Clock(period=timedelta(seconds=settings.JOB_TERMINATION_POLL_INTERVAL))

    while True:
        clock.sleep_until_next_tick()

        try:
            jobs_to_terminate, tasks_to_terminate = get_planned_for_termination()

            for job_id in jobs_to_terminate:
                with atomic(), lock_job_for_termination(job_id) as job_id:
                    if not job_id:
                        continue

                    job = retrieve_job(job_id=job_id)
                    JOB_KILLER_REGISTRY[job.worker["environment"]](job)
                    repo.change_job_status(id=job_id, previous=job.status, new=ExecutionStatus.TERMINATING)

            for task_id in tasks_to_terminate:
                with atomic(), lock_task_for_termination(task_id) as task_id:
                    if not task_id:
                        continue

                    task = retrieve_task(task_id=task_id)
                    TASK_KILLER_REGISTRY[task.worker["environment"]](task)
                    repo.change_task_status(id=task_id, previous=task.status, new=ExecutionStatus.TERMINATING)

        except Exception:  # noqa: BLE001
            logger.exception("Job killer iteration failed")
