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

from collections.abc import Callable, Iterable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Literal, Protocol, TypeAlias
import time

from core.action._types import ExecutionStatus, JobShortInfo, TaskRunnerEnvironment, TaskShortInfo, WorkerInfo
from core.shortcuts import UTC
from core.types import JobID, TaskID


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

        # it will be more precise to use until next tick, but simply calculating now is or for now
        self.next_tick_after = self.now() + self.period


class Terminator(Protocol):
    def terminate_task(self, task: TaskShortInfo) -> None:
        ...

    def terminate_job(self, job: JobShortInfo) -> None:
        ...


TerminatorRegistry: TypeAlias = Mapping[TaskRunnerEnvironment, Terminator]


class TaskLivenessStatus(Enum):
    ALIVE = "alive"
    DEAD = "dead"
    UNKNOWN = "undetectable"


LivenessReport = Mapping[TaskLivenessStatus, list[TaskShortInfo]]


class TaskMonitor(Protocol):
    def analyze_liveness(self, tasks: Iterable[TaskShortInfo]) -> LivenessReport:
        ...


TaskMonitorRegistry: TypeAlias = Mapping[TaskRunnerEnvironment, TaskMonitor]


class TaskQueuer(Protocol):
    env: TaskRunnerEnvironment

    def queue(self, task_id: TaskID) -> WorkerInfo:
        ...


class Claimer(Protocol):
    """
    Claiming a record for exclusive processing is scheduler-specific and may be implemented in various ways
    (e.g. `select_for_update`, external locks), hence kept separate from `JobRepoI`.
    """

    def claim_task(self, task_id: TaskID, expected_status: ExecutionStatus) -> AbstractContextManager[TaskID | None]:
        ...

    def claim_job(self, job_id: JobID, expected_status: ExecutionStatus) -> AbstractContextManager[JobID | None]:
        ...

    def claim_first_scheduled_or_created_task(
        self,
    ) -> AbstractContextManager[tuple[TaskID, Literal[ExecutionStatus.SCHEDULED, ExecutionStatus.CREATED]] | None]:
        """
        Must lock record by id, returning task id and status in order: SCHEDULED, CREATED
        """
        ...
