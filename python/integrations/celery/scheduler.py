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
from datetime import datetime, timedelta
from itertools import chain
from operator import attrgetter, itemgetter
from typing import NewType
import logging

from celery import Celery
from core.action import ExecutionStatus, JobShortInfo, TaskRunnerEnvironment, TaskShortInfo, WorkerInfo
from core.action.job import JobRepoI, JobShortFilter
from core.action.scheduler import LivenessReport, TaskLivenessStatus, TaskMonitor, TaskQueuer, Terminator
from core.shortcuts import UTC
from core.types import TaskID
from django.db.transaction import atomic

from integrations.celery.tasks import run_scheduled_task

monitor_logger = logging.getLogger("scheduler.monitor")

CeleryMonitorTrustGap = NewType("CeleryMonitorTrustGap", timedelta)


@dataclass(slots=True)
class CeleryTerminator(Terminator):
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


@dataclass(slots=True)
class CeleryTaskMonitor(TaskMonitor):
    celery: Celery
    job_repo: JobRepoI
    trust_gap: CeleryMonitorTrustGap

    def analyze_liveness(self, tasks: Iterable[TaskShortInfo]) -> LivenessReport:
        known_celery_task_ids = self.retrieve_known_celery_task_ids()

        monitor_logger.debug("Known celery task ids: %s", known_celery_task_ids)

        # requesting jobs after celery inspect, because celery registeres task id before it appears in database
        tasks_with_jobs = self.retrieve_jobs_for_tasks(tasks)

        result = defaultdict(list)

        for entry in tasks_with_jobs:
            liveness_status = self.is_alive(task_with_jobs=entry, celery_task_ids=known_celery_task_ids)
            result[liveness_status].append(entry[0])

        monitor_logger.debug("Liveness check result: %s", result)

        return result

    def retrieve_known_celery_task_ids(self) -> set[str]:
        celery_inspect = self.celery.control.inspect()
        # If there are no nodes, the commands return None, and we cast them into an empty dictionary
        reserved_celery_tasks = celery_inspect.reserved() or {}
        scheduled_celery_tasks = celery_inspect.scheduled() or {}
        active_celery_tasks = celery_inspect.active() or {}

        return set(
            map(
                itemgetter("id"),
                chain.from_iterable(
                    chain(scheduled_celery_tasks.values(), active_celery_tasks.values(), reserved_celery_tasks.values())
                ),
            )
        )

    def retrieve_jobs_for_tasks(
        self, tasks: Iterable[TaskShortInfo]
    ) -> tuple[tuple[TaskShortInfo, list[JobShortInfo]], ...]:
        tasks_to_analyze = tuple(tasks)

        # requesting jobs after celery inspect, because celery registeres task id before it appears in database
        jobs: tuple[JobShortInfo, ...] = tuple(
            self.job_repo.find_jobs_short(JobShortFilter(task_ids=map(attrgetter("id"), tasks_to_analyze)))
        )

        jobs_per_task: dict[int, list[JobShortInfo]] = defaultdict(list)
        for job in jobs:
            jobs_per_task[job.task_id].append(job)

        return tuple((task, jobs_per_task.get(task.id, [])) for task in tasks_to_analyze)

    def is_alive(
        self, task_with_jobs: tuple[TaskShortInfo, list[JobShortInfo]], celery_task_ids: set[str]
    ) -> TaskLivenessStatus:
        task, jobs = task_with_jobs
        task_related_celery_ids = {task.worker.get("worker_id"), *(job.worker.get("worker_id") for job in jobs)} - {
            None
        }
        if task_related_celery_ids.intersection(celery_task_ids):
            return TaskLivenessStatus.ALIVE

        # finish_dates will be missing for tasks with one or the first running job.
        # Meanwhile, the trust gap is needed to “give time” for the new job to start
        # (and therefore it will be displayed in the scheduled or active list)
        # If none of the jobs have a finish_date assigned and they are not listed in the set above,
        # this most likely means that there’s no point in waiting for the trust gap in the hope that it will appear.
        finish_dates = tuple(filter(None, map(attrgetter("finish_date"), jobs)))

        if finish_dates:
            latest_finished_job_date = max(finish_dates)

            unknown_threshold = datetime.now(tz=UTC) - self.trust_gap

            if latest_finished_job_date > unknown_threshold:
                return TaskLivenessStatus.UNKNOWN

        return TaskLivenessStatus.DEAD


class CeleryTaskQueuer(TaskQueuer):
    env = TaskRunnerEnvironment.CELERY

    def queue(self, task_id: TaskID) -> WorkerInfo:
        # disabled during jobs.scheduler/integrations.celery move, code wasn't pyright-checked before, must be reviewed
        result = run_scheduled_task.delay(task_id=task_id)  # pyright: ignore[reportCallIssue]

        return WorkerInfo(environment=self.env, worker_id=result.id)
