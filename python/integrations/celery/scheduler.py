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
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from operator import attrgetter, itemgetter
from typing import Literal, NewType
import logging

from celery import Celery
from core.action import (
    UNFINISHED_STATUSES,
    ExecutionStatus,
    JobShortInfo,
    TaskRunnerEnvironment,
    TaskShortInfo,
    WorkerInfo,
)
from core.action.job import JobRepoI, JobShortFilter
from core.action.scheduler import LivenessReport, TaskLivenessStatus, TaskMonitor, TaskQueuer, Terminator
from core.types import JobID, TaskID
from django.db import DatabaseError
from django.db.transaction import atomic

from integrations.celery.pg.kombu import list_messages
from integrations.celery.tasks import run_scheduled_task

monitor_logger = logging.getLogger("scheduler.monitor")

CeleryMonitorTrustGap = NewType("CeleryMonitorTrustGap", timedelta)


@dataclass(frozen=True, slots=True)
class UntrackedJob:
    id: JobID
    since: datetime
    status: ExecutionStatus


@dataclass(frozen=True, slots=True)
class MessageIndex:
    celery_task_ids: frozenset[str]
    adcm_job_ids: frozenset[JobID]

    def has_message_for_job(self, job: JobShortInfo) -> bool:
        return job.id in self.adcm_job_ids or (
            job.worker.worker_id is not None and job.worker.worker_id in self.celery_task_ids
        )


@dataclass(slots=True)
class CeleryTerminator(Terminator):
    app: Celery
    repo: JobRepoI

    def terminate_task(self, task: TaskShortInfo) -> None:
        with atomic():
            self.repo.change_status_of_task_jobs(
                task_id=task.id, previous=(ExecutionStatus.CREATED,), new=ExecutionStatus.REVOKED
            )

        jobs = self.repo.find_jobs_short(JobShortFilter(task_ids=[task.id]))
        # we assume that jobs can't be in scheduled/queued statuses,
        # when REVOKING/TERMINATING is uninteresting for this process,
        # it should be independent (at least I see it like that for now)
        running_jobs = tuple(job for job in jobs if job.status == ExecutionStatus.RUNNING)
        job_id_celery_task_id_pairs = tuple(map(attrgetter("id", "worker.worker_id"), running_jobs))

        celery_task_ids = list(filter(None, map(itemgetter(1), job_id_celery_task_id_pairs)))
        if celery_task_ids:
            self.app.control.revoke(task_id=celery_task_ids)

        # there should be exactly 1 running job, so it isn't big N+1 problem
        for job_id, celery_task_id in job_id_celery_task_id_pairs:
            self.send_stop_executor_signal_for_job(job_id=job_id, celery_task_id=celery_task_id)

    def terminate_job(self, job: JobShortInfo) -> None:
        self.send_stop_executor_signal_for_job(job_id=job.id, celery_task_id=job.worker.worker_id)

    def send_stop_executor_signal_for_job(self, job_id: int, celery_task_id: str | int | None) -> None:
        self.app.control.broadcast(
            "stop_executor", arguments={"task_id": celery_task_id, "adcm_job_id": str(job_id or "")}
        )


@dataclass(slots=True)
class CeleryTaskMonitor(TaskMonitor):
    celery: Celery
    job_repo: JobRepoI
    trust_gap: CeleryMonitorTrustGap
    task_interruption_mode: Literal["any_job_lost", "all_jobs_lost"] = "all_jobs_lost"
    unknown_state_tasks: dict[TaskID, list[UntrackedJob]] = field(default_factory=dict, init=False, repr=False)

    def analyze_liveness(self, tasks: Iterable[TaskShortInfo]) -> LivenessReport:
        messages = retrieve_message_index()
        celery_inspect = self.celery.control.inspect()
        known_celery_task_ids = self.retrieve_known_celery_task_ids(celery_inspect)
        monitor_logger.debug("Known celery task ids: %s", known_celery_task_ids)
        # requesting jobs after celery inspect, because celery registeres task id before it appears in database
        tasks_with_jobs = self.retrieve_jobs_for_tasks(tasks)

        current_task_ids = {task.id for task, _ in tasks_with_jobs}
        # Drop saved UNKNOWN snapshots for tasks no longer included in this pass,
        # e.g. tasks that finished or became BROKEN and left the QUEUED/RUNNING/TERMINATING selection.
        for task_id in self.unknown_state_tasks.keys() - current_task_ids:
            self.clear_unknown_task(task_id)

        result = defaultdict(list)
        for entry in tasks_with_jobs:
            status = self.get_liveness_status(
                task_with_jobs=entry,
                celery_task_ids=known_celery_task_ids,
                messages=messages,
            )
            result[status].append(entry[0])
        monitor_logger.debug("Liveness check result: %s", result)

        return result

    def retrieve_known_celery_task_ids(self, celery_inspect) -> set[str]:
        reserved_celery_tasks = celery_inspect.reserved() or {}
        scheduled_celery_tasks = celery_inspect.scheduled() or {}
        active_celery_tasks = celery_inspect.active() or {}
        reserved_ids = {task["id"] for worker_tasks in reserved_celery_tasks.values() for task in worker_tasks}
        scheduled_ids = {
            task["request"]["id"] for worker_tasks in scheduled_celery_tasks.values() for task in worker_tasks
        }
        active_ids = {task["id"] for worker_tasks in active_celery_tasks.values() for task in worker_tasks}

        return reserved_ids | scheduled_ids | active_ids

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

    def get_liveness_status(
        self,
        task_with_jobs: tuple[TaskShortInfo, list[JobShortInfo]],
        celery_task_ids: set[str],
        messages: MessageIndex,
    ) -> TaskLivenessStatus:
        task, jobs = task_with_jobs

        tracked_jobs, problem_jobs = self._get_analyzed_jobs(
            jobs_to_check=jobs,
            celery_task_ids=celery_task_ids,
            messages=messages,
        )

        if not problem_jobs or (self.task_interruption_mode == "all_jobs_lost" and tracked_jobs):
            self.clear_unknown_task(task.id)
            return TaskLivenessStatus.ALIVE

        now = datetime.now(tz=timezone.utc)
        previous_jobs = {job.id: job for job in self.unknown_state_tasks.get(task.id, [])}
        problem_jobs_statuses = {job.id: job.status for job in jobs if job.id in problem_jobs}
        # Keep a job's timer only while it remains untracked with the same ADCM status.
        untracked_jobs = []
        for job_id, status in problem_jobs_statuses.items():
            previous_job = previous_jobs.get(job_id)
            if previous_job is not None and previous_job.status == status:
                untracked_jobs.append(previous_job)
            else:
                untracked_jobs.append(UntrackedJob(id=job_id, since=now, status=status))
        self.unknown_state_tasks[task.id] = untracked_jobs

        expired_jobs = [job.id for job in untracked_jobs if now - job.since >= self.trust_gap]
        if expired_jobs:
            monitor_logger.warning("ADCM task %s exceeded UNKNOWN trust gap; problem jobs: %s", task.id, expired_jobs)
            return TaskLivenessStatus.DEAD

        return TaskLivenessStatus.UNKNOWN

    def _get_analyzed_jobs(
        self,
        *,
        jobs_to_check: Iterable[JobShortInfo],
        celery_task_ids: set[str],
        messages: MessageIndex,
    ) -> tuple[set[JobID], set[JobID]]:
        """Find tracked and untracked jobs."""
        tracked_jobs: set[JobID] = set()
        untracked_jobs: set[JobID] = set()
        for job in jobs_to_check:
            if job.status not in UNFINISHED_STATUSES:
                continue

            is_tracked = (
                job.worker.worker_id is not None and job.worker.worker_id in celery_task_ids
            ) or messages.has_message_for_job(job)
            if is_tracked:
                tracked_jobs.add(job.id)
                continue

            is_submitted = job.status != ExecutionStatus.CREATED or job.worker.worker_id is not None
            if is_submitted:
                untracked_jobs.add(job.id)

        return tracked_jobs, untracked_jobs

    def clear_unknown_task(self, task_id: TaskID) -> None:
        """Remove a task from UNKNOWN tracking."""
        self.unknown_state_tasks.pop(task_id, None)


class CeleryTaskQueuer(TaskQueuer):
    env = TaskRunnerEnvironment.CELERY

    def queue(self, task_id: TaskID) -> WorkerInfo:
        # disabled during jobs.scheduler/integrations.celery move, code wasn't pyright-checked before, must be reviewed
        result = run_scheduled_task.delay(task_id=task_id)  # pyright: ignore[reportCallIssue]

        return WorkerInfo(environment=self.env, worker_id=result.id)


def retrieve_message_index() -> MessageIndex:
    """Read visible and claimed messages once and index both Celery UUIDs and ADCM job IDs."""
    try:
        messages = list_messages()
    except DatabaseError:
        monitor_logger.exception("Failed to read Kombu messages due to a database or connection error")
        return MessageIndex(celery_task_ids=frozenset(), adcm_job_ids=frozenset())

    celery_task_ids = set()
    adcm_job_ids = set()
    for message in messages:
        if message.error is not None:
            monitor_logger.debug(message.error)
            continue
        if message.celery_task_id is not None:
            celery_task_ids.add(message.celery_task_id)
        if message.adcm_job_id is not None:
            adcm_job_ids.add(message.adcm_job_id)

    return MessageIndex(
        celery_task_ids=frozenset(celery_task_ids),
        adcm_job_ids=frozenset(adcm_job_ids),
    )
