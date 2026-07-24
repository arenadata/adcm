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

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from operator import attrgetter, itemgetter
from typing import Protocol, TypeAlias
import os
import time

from celery import Celery
from core.action import ExecutionStatus
from core.action.job import ExecutorTerminator, JobRepoI, TaskRunnerTerminator
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


# NOTE:
#   "Killer" as term is colliding with "Terminator" one,
#   rethink them in case of uni/core-fication


class Killer(Protocol):
    def terminate_task(self, task: TaskShortInfo) -> None:
        ...

    def terminate_job(self, job: JobShortInfo) -> None:
        ...


KillerRegistry: TypeAlias = Mapping[TaskRunnerEnvironment, Killer]


@dataclass(slots=True)
class LocalKiller(Killer):
    task_runner_terminator: TaskRunnerTerminator
    executor_terminator: ExecutorTerminator

    def terminate_task(self, task: TaskShortInfo) -> None:
        self.task_runner_terminator.terminate(int(task.worker["worker_id"]))

    def terminate_job(self, job: JobShortInfo) -> None:
        self.executor_terminator.terminate(int(job.worker["worker_id"]))


@dataclass(slots=True)
class CeleryKiller(Killer):
    app: Celery
    repo: JobRepoI

    def terminate_task(self, task: TaskShortInfo) -> None:
        with atomic():
            self.repo.change_status_of_task_jobs(
                task_id=task.id, previous=ExecutionStatus.CREATED, new=ExecutionStatus.REVOKED
            )

        jobs = self.repo.find_jobs_of_task(task.id)
        # we assume that jobs can't be in scheduled/queued statuses,
        # when REVOKING/TERMINATING is uninteresting for this process,
        # it should be independent (at least I see it like that for now)
        running_jobs = tuple(job for job in jobs if job.status == ExecutionStatus.RUNNING)
        job_id_celery_task_id_pairs = tuple(map(attrgetter("id", "execution_env.worker_id"), running_jobs))

        celery_task_ids = list(filter(None, map(itemgetter(1), job_id_celery_task_id_pairs)))
        if celery_task_ids:
            self.app.control.revoke(task_id=celery_task_ids)

        # there should be exactly 1 running job, so it isn't big N+1 problem
        for job_id, celery_task_id in job_id_celery_task_id_pairs:
            self.send_stop_executor_signal_for_job(job_id=job_id, celery_task_id=celery_task_id)

    def terminate_job(self, job: JobShortInfo) -> None:
        self.send_stop_executor_signal_for_job(job_id=job.id, celery_task_id=job.worker["worker_id"])

    def send_stop_executor_signal_for_job(self, job_id: int, celery_task_id: str | int | None) -> None:
        self.app.control.broadcast(
            "stop_executor", arguments={"task_id": celery_task_id, "adcm_job_id": str(job_id or "")}
        )


def run_killer_in_loop(container: dishka.Container) -> None:
    logger.info("Job killer started (pid: %s)", os.getpid())

    repo: JobRepoI = container.get(JobRepoI)
    registry = container.get(KillerRegistry)

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

                    logger.debug("Scheduler.Killer terminating job with id=%d started", job_id)

                    job = retrieve_job(job_id=job_id)
                    killer = registry[job.worker["environment"]]
                    killer.terminate_job(job)
                    status_changed = repo.change_job_status(
                        id=job_id, previous=job.status, new=ExecutionStatus.TERMINATING
                    )

                    logger.debug(
                        "Scheduler.Killer terminating job with id=%d finished, status changed = %s",
                        job_id,
                        status_changed,
                    )

            for task_id in tasks_to_terminate:
                with atomic(), lock_task_for_termination(task_id) as task_id:
                    if not task_id:
                        continue

                    logger.debug("Scheduler.Killer terminating task with id=%d started", task_id)

                    task = retrieve_task(task_id=task_id)
                    killer = registry[task.worker["environment"]]
                    killer.terminate_task(task)
                    status_changed = repo.change_task_status(
                        id=task_id, previous=task.status, new=ExecutionStatus.TERMINATING
                    )

                    logger.debug(
                        "Scheduler.Killer terminating task with id=%d finished, status changed = %s",
                        task_id,
                        status_changed,
                    )

        except Exception:  # noqa: BLE001
            logger.exception("Job killer iteration failed")
