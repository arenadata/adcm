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
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from itertools import chain
from operator import attrgetter, itemgetter
from typing import NewType, Protocol, TypeAlias
import os
import logging

from celery import Celery
from core.legacy.job.runners import RunnerEnvironment
from core.result import Fail, Success
from use_cases.job.run import MarkTaskBroken

from jobs.scheduler import repo
from jobs.scheduler.clock import Clock
from jobs.scheduler.types import UTC, JobShortInfo, TaskRunnerEnvironment, TaskShortInfo
from jobs.scheduler.utils import is_pid_exists

logger = logging.getLogger("scheduler.monitor")


class TaskLivenessStatus(Enum):
    ALIVE = "alive"
    DEAD = "dead"
    UNKNOWN = "undetectable"


LivenessReport = Mapping[TaskLivenessStatus, list[TaskShortInfo]]


class TaskMonitor(Protocol):
    def analyze_liveness(self, tasks: Iterable[TaskShortInfo]) -> LivenessReport:
        ...


TaskMonitorRegistry: TypeAlias = Mapping[TaskRunnerEnvironment, TaskMonitor]


@dataclass(slots=True)
class LocalTaskMonitor(TaskMonitor):
    def analyze_liveness(self, tasks: Iterable[TaskShortInfo]) -> LivenessReport:
        result = defaultdict(list)

        for task in tasks:
            liveness_status = self.is_alive(task)
            result[liveness_status].append(task)

        logger.debug("Liveness check result: %s", result)

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


CeleryMonitorTrustGap = NewType("CeleryMonitorTrustGap", timedelta)


@dataclass(slots=True)
class CeleryTaskMonitor(TaskMonitor):
    celery: Celery
    scheduler_repo: repo.SchedulerRepo
    trust_gap: CeleryMonitorTrustGap

    def analyze_liveness(self, tasks: Iterable[TaskShortInfo]) -> LivenessReport:
        known_celery_task_ids = self.retrieve_known_celery_task_ids()

        logger.debug("Known celery task ids: %s", known_celery_task_ids)

        # requesting jobs after celery inspect, because celery registeres task id before it appears in database
        tasks_with_jobs = self.retrieve_jobs_for_tasks(tasks)

        # Analysis

        result = defaultdict(list)

        for entry in tasks_with_jobs:
            liveness_status = self.is_alive(task_with_jobs=entry, celery_task_ids=known_celery_task_ids)
            result[liveness_status].append(entry[0])

        logger.debug("Liveness check result: %s", result)

        return result

    def retrieve_known_celery_task_ids(self) -> set[str]:
        celery_inspect = self.celery.control.inspect()
        scheduled_celery_tasks = celery_inspect.scheduled()
        active_celery_tasks = celery_inspect.active()

        return set(
            map(
                itemgetter("id"),
                chain.from_iterable(chain(scheduled_celery_tasks.values(), active_celery_tasks.values())),
            )
        )

    def retrieve_jobs_for_tasks(
        self, tasks: Iterable[TaskShortInfo]
    ) -> tuple[tuple[TaskShortInfo, list[JobShortInfo]], ...]:
        tasks_to_analyze = tuple(tasks)

        # requesting jobs after celery inspect, because celery registeres task id before it appears in database
        jobs: tuple[JobShortInfo, ...] = tuple(
            self.scheduler_repo.retrieve_jobs(task_id__in=map(attrgetter("id"), tasks_to_analyze))
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

        latest_finished_job_date = max(filter(None, map(attrgetter("finish_date"), jobs)))
        unknown_threshold = datetime.now(tz=UTC) - self.trust_gap
        if latest_finished_job_date > unknown_threshold:
            return TaskLivenessStatus.UNKNOWN

        return TaskLivenessStatus.DEAD


MonitorClock = NewType("MonitorClock", Clock)


@dataclass(slots=True)
class Monitor:
    set_broken: MarkTaskBroken
    running_environment: RunnerEnvironment
    registry: TaskMonitorRegistry
    scheduler_repo: repo.SchedulerRepo
    clock: MonitorClock

    def run_in_loop(self):
        logger.info("Monitor started (pid: %d)", os.getpid())

        while True:
            self.clock.sleep_until_next_tick()

            try:
                self.run_iteration()
            except Exception:  # noqa: BLE001
                logger.exception("Skipping monitor iteration due to exception:")

    def run_iteration(self):
        tasks_to_check: Iterable[TaskShortInfo] = self.scheduler_repo.retrieve_tasks_for_monitoring()

        grouped_by_environment: dict[TaskRunnerEnvironment, list[TaskShortInfo]] = defaultdict(list)
        for task in tasks_to_check:
            grouped_by_environment[task.worker["environment"]].append(task)

        for environment, tasks in grouped_by_environment.items():
            task_monitor = self.registry[environment]
            result = task_monitor.analyze_liveness(tasks)

            for dead_task in result.get(TaskLivenessStatus.DEAD, ()):
                logger.debug("Task id=%d is considered dead, setting to broken", dead_task.id)

                result = self.set_broken.do(
                    task_id=dead_task.id, environment=self.running_environment, from_status=dead_task.status
                )
                match result:
                    case Success():
                        logger.debug("Task id=%d set to broken successfuly", dead_task.id)
                    case Fail(msg):
                        logger.debug("Task id=%d set to broken failed: %s", dead_task.id, msg)
