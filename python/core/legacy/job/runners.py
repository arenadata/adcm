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
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Protocol

from core.action import ExecutionStatus, Job, Task
from core.action.job import JobRepoI
from core.cluster import ClusterService
from core.legacy.job.executors import Executor


class ADCMSettings(NamedTuple):
    code_root_dir: Path
    run_dir: Path
    log_dir: Path


class AnsibleSettings(NamedTuple):
    ansible_secret_script: Path


class IntegrationsSettings(NamedTuple):
    status_server_token: str


class ConsulSettings(NamedTuple):
    url: str | None
    datacenter: str | None
    cacert_file: str | None


class ExternalSettings(NamedTuple):
    adcm: ADCMSettings
    ansible: AnsibleSettings
    integrations: IntegrationsSettings
    consul: ConsulSettings


class JobFinalizer(Protocol):
    def __call__(self, job: Job) -> None:
        ...


class JobEnvironmentBuilder(Protocol):
    def __call__(
        self,
        task: Task,
        job: Job,
        configuration: ExternalSettings,
        cluster_service: ClusterService,
    ) -> None:
        ...


class ExecutionTarget(NamedTuple):
    job: Job
    executor: Executor
    environment_builders: Iterable[JobEnvironmentBuilder]
    # stuff like `finish_check` should go to finalizers
    finalizers: Iterable[JobFinalizer]


class ExecutionTargetFactoryI(Protocol):
    def __call__(self, task: Task, jobs: Iterable[Job], configuration: ExternalSettings) -> Iterable[ExecutionTarget]:
        ...


def always_true(_: "Job") -> bool:
    return True


class JobFilterPredicate(Protocol):
    def __call__(self, job: Job, /) -> bool:
        ...


@dataclass(slots=True)
class JobProcessor:
    convert: ExecutionTargetFactoryI
    filter_predicate: JobFilterPredicate = always_true


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
    _repo: JobRepoI
    _environment: RunnerEnvironment

    _runtime: RunnerRuntime

    def __init__(
        self,
        *,
        job_processor: JobProcessor,
        settings: ExternalSettings,
        repo: JobRepoI,
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
