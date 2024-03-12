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

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, NamedTuple, Protocol

from core.job.executors import Executor
from core.job.repo import JobRepoInterface
from core.job.types import ExecutionStatus, Job, Task


class ADCMSettings(NamedTuple):
    code_root_dir: Path
    run_dir: Path
    log_dir: Path


class AnsibleSettings(NamedTuple):
    ansible_secret_script: Path


class IntegrationsSettings(NamedTuple):
    status_server_token: str


class ExternalSettings(NamedTuple):
    adcm: ADCMSettings
    ansible: AnsibleSettings
    integrations: IntegrationsSettings


class JobFinalizer(Protocol):
    def __call__(self, job: Job) -> None:
        ...


class JobEnvironmentBuilder(Protocol):
    def __call__(self, task: Task, job: Job, configuration: ExternalSettings) -> None:
        ...


class ExecutionTarget(NamedTuple):
    job: Job
    executor: Executor
    environment_builders: Iterable[JobEnvironmentBuilder]
    # stuff like `finish_check` should go to finalizers
    finalizers: Iterable[JobFinalizer]


class JobToExecutionTargetConverter(Protocol):
    def __call__(self, task: Task, jobs: Iterable[Job], configuration: ExternalSettings) -> Iterable[ExecutionTarget]:
        ...


class JobProcessor(NamedTuple):
    convert: JobToExecutionTargetConverter
    # id will always return True in bool cast
    filter_predicate: Callable[[Job], bool] = id


class RunnerEnvironment(Protocol):
    pid: int

    def now(self) -> datetime:
        ...


@dataclass(slots=True)
class Termination:
    is_requested: bool = False


@dataclass(slots=True)
class RunnerRuntime:
    task_id: int
    status: ExecutionStatus = ExecutionStatus.CREATED
    termination: Termination = field(default_factory=Termination)


class TaskRunner(ABC):
    _job_processor: JobProcessor
    _settings: ExternalSettings

    # external dependencies
    _repo: JobRepoInterface
    _environment: RunnerEnvironment

    _runtime: RunnerRuntime

    def __init__(
        self,
        *,
        job_processor: JobProcessor,
        settings: ExternalSettings,
        repo: JobRepoInterface,
        environment: RunnerEnvironment,
    ):
        self._job_processor = job_processor
        self._settings = settings
        self._repo = repo
        self._environment = environment
        self._runtime = RunnerRuntime(task_id=-1)

    @abstractmethod
    def run(self, task_id: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    def terminate(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def consider_broken(self) -> None:
        raise NotImplementedError()
