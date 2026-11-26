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

from core.action import ExecutionStatus, Task
from core.action.job import JobRepoI
from core.action.types import (
    AnsibleScript,
    ConfigApplyScript,
    HcApplyScript,
    InternalScript,
    JobShortInfo,
    PythonScript,
    RichJob,
    ServiceManageScript,
    SimpleInternalScript,
)
from core.cluster import ClusterService
from core.config import ConfigService
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
    def __call__(self, job: RichJob) -> None: ...


class JobEnvironmentBuilder(Protocol):
    def __call__(
        self,
        task: Task,
        job: RichJob,
        configuration: ExternalSettings,
        cluster_service: ClusterService,
        config_service: ConfigService,
    ) -> None: ...


@dataclass(slots=True)
class ExecutionTarget:
    executor: Executor
    environment_builders: Iterable[JobEnvironmentBuilder]
    # stuff like `finish_check` should go to finalizers
    finalizers: Iterable[JobFinalizer]


class AnsibleTargetBuilderI(Protocol):
    def __call__(
        self, script: AnsibleScript, task: Task, job: JobShortInfo, configuration: ExternalSettings
    ) -> ExecutionTarget: ...


class PythonTargetBuilderI(Protocol):
    def __call__(
        self, script: PythonScript, task: Task, job: JobShortInfo, configuration: ExternalSettings
    ) -> ExecutionTarget: ...


class InternalTargetBuilderI(Protocol):
    def __call__(
        self, script: InternalScript, task: Task, job: JobShortInfo, configuration: ExternalSettings
    ) -> ExecutionTarget: ...


@dataclass(slots=True)
class ExecutionTargetFactory:
    ansible: AnsibleTargetBuilderI
    python: PythonTargetBuilderI
    internal: InternalTargetBuilderI

    def __call__(self, task: Task, job: RichJob, configuration: ExternalSettings) -> ExecutionTarget:
        match job.spec.script:
            case AnsibleScript() as script:
                return self.ansible(script=script, task=task, job=job.runtime, configuration=configuration)
            case PythonScript() as script:
                return self.python(script=script, task=task, job=job.runtime, configuration=configuration)
            case (SimpleInternalScript() | HcApplyScript() | ConfigApplyScript() | ServiceManageScript()) as script:
                return self.internal(script=script, task=task, job=job.runtime, configuration=configuration)
            case _:
                message = f"Can't convert job of type {job.spec.script.type}"
                raise NotImplementedError(message)


class RunnerEnvironment(Protocol):
    pid: int

    def now(self) -> datetime: ...


@dataclass(slots=True)
class Termination:
    is_requested: bool = False


@dataclass(slots=True)
class RunnerRuntime:
    task_id: int
    status: ExecutionStatus = ExecutionStatus.CREATED
    termination: Termination = field(default_factory=Termination)


class TaskRunner(ABC):
    _target_factory: ExecutionTargetFactory
    _settings: ExternalSettings

    # external dependencies
    _repo: JobRepoI
    _environment: RunnerEnvironment

    _runtime: RunnerRuntime

    def __init__(
        self,
        *,
        target_factory: ExecutionTargetFactory,
        settings: ExternalSettings,
        repo: JobRepoI,
        environment: RunnerEnvironment,
    ):
        self._target_factory = target_factory
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
