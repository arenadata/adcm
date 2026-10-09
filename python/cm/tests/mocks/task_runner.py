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

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NamedTuple

from core.action import Task
from core.action.types import AnsibleScript, JobShortInfo, PythonScript
from core.legacy.job.executors import ExecutionResult, Executor, ExecutorConfig
from core.legacy.job.runners import AnsibleTargetBuilderI, ExecutionTarget, ExternalSettings, PythonTargetBuilderI
from core.spec.types import FullSpecKey
from django.utils import timezone
from typing_extensions import Self

from cm.impl.job.repo import JobRepo


def do_nothing(*_, **__):
    return None


class FailedJobInfo(NamedTuple):
    spec_key: FullSpecKey
    return_code: int = 1


class JobImitator(NamedTuple):
    call: Callable[[Executor], Any] = do_nothing
    return_code: int = 0
    use_call_return_code: bool = False


default_imitator = JobImitator()


# ExecutionTarget Factories


@dataclass(slots=True)
class TargetBuilderDummyMock:
    failed_job: FailedJobInfo | None = None

    def __call__(
        self,
        script: AnsibleScript | PythonScript,
        task: Task,  # noqa: ARG002
        job: JobShortInfo,
        configuration: ExternalSettings,
    ) -> ExecutionTarget:
        imitator = default_imitator
        if self.failed_job is not None and job.spec_key == self.failed_job.spec_key:
            imitator = JobImitator(return_code=self.failed_job.return_code)

        executor = MockExecutor(
            script_type=script.path,
            imitator=imitator,
            config=ExecutorConfig(work_dir=configuration.adcm.run_dir / str(job.id)),
        )

        return ExecutionTarget(executor=executor, environment_builders=(), finalizers=())


@dataclass(slots=True)
class TargetBuilderWithEnvMock:
    origin: AnsibleTargetBuilderI | PythonTargetBuilderI
    change_jobs: dict[FullSpecKey, JobImitator] | None = None

    def __call__(
        self, script: AnsibleScript | PythonScript, task: Task, job: JobShortInfo, configuration: ExternalSettings
    ) -> ExecutionTarget:
        target = self.origin(script=script, task=task, job=job, configuration=configuration)
        executor = MockExecutor(
            script_type=target.executor.script_type,
            config=ExecutorConfig(work_dir=configuration.adcm.run_dir / str(job.id)),
            imitator=(self.change_jobs or {}).get(job.spec_key, default_imitator),
        )

        return ExecutionTarget(
            executor=executor, environment_builders=target.environment_builders, finalizers=target.finalizers
        )


# Executors


class MockExecutor(Executor):
    def __init__(self, *args, script_type: str = "ansible", imitator: JobImitator = default_imitator, **kwargs):
        super().__init__(*args, **kwargs)

        self._script_type = script_type

        if imitator.return_code < 0:
            message = "Only integers >= 0 are allowed as return code"
            raise ValueError(message)

        self._imitator = imitator

    @property
    def script_type(self) -> str:
        return self._script_type

    def execute(self) -> Self:
        result = self._imitator.call(self)
        code = result if self._imitator.use_call_return_code else self._imitator.return_code
        self._result = ExecutionResult(code=code)
        return self

    def wait_finished(self) -> Self:
        return self


# Custom Mocks


class SubprocessRunnerMockEnvironment:
    @property
    def pid(self) -> int:
        return 5_000_000

    def now(self) -> datetime:
        return timezone.now()


class JobImplRunnerMock(JobRepo):
    def close_old_connections(self) -> None:
        return
