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
from enum import Enum
from typing import Literal, TypeAlias, TypedDict

from core.types import TaskID

WorkerID: TypeAlias = int


class TaskRunnerEnvironment(str, Enum):
    LOCAL = "local"
    CELERY = "celery"


class WorkerInfo(TypedDict):
    environment: Literal["local", "celery"]
    worker_id: WorkerID


class TaskQueuer(ABC):
    env: TaskRunnerEnvironment

    @abstractmethod
    def queue(self, task_id: TaskID) -> WorkerInfo:
        ...
