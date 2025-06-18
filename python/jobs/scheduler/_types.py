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

# The file is named this way to avoid circular imports.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, TypeAlias, TypedDict

from core.job.types import ExecutionStatus
from core.types import ActionID, ConcernID, TaskID
import zoneinfo

###########
# Constants
###########


UTC = zoneinfo.ZoneInfo("UTC")


class CeleryTaskState(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    RETRY = "RETRY"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"
    ADCM_UNREACHABLE = "ADCM-UNREACHABLE"


class _ADCMStatus(NamedTuple):
    recover_status: ExecutionStatus | None
    is_final: bool


CELERY_STATE_ADCM_STATUS_MAP = {
    CeleryTaskState.PENDING: _ADCMStatus(recover_status=None, is_final=False),
    CeleryTaskState.STARTED: _ADCMStatus(recover_status=None, is_final=False),
    CeleryTaskState.RETRY: _ADCMStatus(recover_status=None, is_final=False),
    CeleryTaskState.FAILURE: _ADCMStatus(recover_status=ExecutionStatus.BROKEN, is_final=True),
    CeleryTaskState.SUCCESS: _ADCMStatus(recover_status=ExecutionStatus.SUCCESS, is_final=True),
    # TODO: retry getting an actual state before considering final/broken?
    CeleryTaskState.ADCM_UNREACHABLE: _ADCMStatus(recover_status=ExecutionStatus.BROKEN, is_final=True),
}

CELERY_RUNNING_STATES = {
    state for state, adcm_status in CELERY_STATE_ADCM_STATUS_MAP.items() if not adcm_status.is_final
}


#######
# Types
#######


WorkerID: TypeAlias = int | str


class TaskRunnerEnvironment(str, Enum):
    LOCAL = "local"
    CELERY = "celery"


class WorkerInfo(TypedDict):
    environment: TaskRunnerEnvironment
    worker_id: WorkerID


@dataclass
class ActionShortInfo:
    id: ActionID
    is_mm_action: bool


@dataclass(slots=True, frozen=True)
class TaskShortInfo:
    id: TaskID
    worker: WorkerInfo
    status: ExecutionStatus
    lock_id: ConcernID | None
    action: ActionShortInfo


class LiveCheckResult(NamedTuple):
    is_dead: bool
    status: ExecutionStatus | None = None


######
# ABCs
######


class TaskQueuer(ABC):
    env: TaskRunnerEnvironment

    @abstractmethod
    def queue(self, task_id: TaskID) -> WorkerInfo:
        ...
