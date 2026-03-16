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

from dataclasses import dataclass, field
from functools import cache, partial
from pathlib import Path
from tempfile import gettempdir
from typing import Iterable
from unittest.mock import patch
from uuid import uuid4
import os

from application.di.containers import get_main_providers
from cm.models import TaskLog
from cm.tests.mocks.task_runner import (
    ETFMockWithEnvPreparation,
    ExecutionTargetFactoryDummyMock,
    FailedJobInfo,
    JobImitator,
    JobImplRunnerMock,
    SubprocessRunnerMockEnvironment,
)
from core import secrets
from core.files.directories import ADCMBundleDir
from core.legacy.job.repo import JobRepoInterface
from core.legacy.job.runners import (
    ADCMSettings,
    AnsibleSettings,
    ConsulSettings,
    ExecutionTargetFactoryI,
    ExternalSettings,
    IntegrationsSettings,
    JobFilterPredicate,
    JobProcessor,
    RunnerEnvironment,
    TaskRunner,
    always_true,
)
from core.result import Success
from core.settings import Directories
from core.types import PID, CurrentADCMVersion, TaskID
from dishka.provider import provide
from use_cases.transition.job.schedule import TaskStarter
import dishka

_PYTHON_DIR = python_dir = Path(__file__).parent.parent.parent.parent


@dataclass(slots=True)
class FakePopen:
    pid: int


@dataclass(slots=True)
class LaunchedTaskInTest:
    id: TaskID


@dataclass()
class TaskRunnerTestManager:
    _latest_launched: LaunchedTaskInTest | None = field(default=None)

    def start(self, task_orm: TaskLog) -> PID:
        if self._latest_launched:
            raise RuntimeError("Not it is not possible to run two tasks without 'reset'")

        # for now patch feels easier that copying actual start

        from cm.legacy.services.job.run._task import start_task

        with patch("cm.legacy.services.job.run._task.subprocess.Popen", return_value=FakePopen(pid=-1)):
            result = start_task(task_orm)

        self._latest_launched = LaunchedTaskInTest(id=task_orm.pk)

        return result

    def reset(self) -> None:
        self._latest_launched = None

    def expect_task_launched(self, task_id: int | None = None) -> LaunchedTaskInTest:
        assert self._latest_launched  # noqa: S101
        launched = self._latest_launched
        if task_id is not None:
            assert launched.id == task_id  # noqa: S101
        return launched

    def expect_task_not_launched(self) -> None:
        assert self._latest_launched is None  # noqa: S101

    def run_launched_task(self, task_id: TaskID | None = None, overrides: Iterable[dishka.Provider] = ()) -> None:
        task_id_ = self.expect_task_launched(task_id).id
        self.run_task(task_id=task_id_, overrides=overrides)

    def run_task(self, task_id: TaskID, overrides: Iterable[dishka.Provider] = ()) -> None:
        container = dishka.make_container(*get_default_overridden_providers(), *overrides)

        with container(context={JobFilterPredicate: always_true}):
            runner = container.get(TaskRunner)
            runner.run(task_id=task_id)


@cache
def get_task_runner_manager() -> TaskRunnerTestManager:
    return TaskRunnerTestManager()


@cache
def prepare_process_bound_directories() -> Directories:
    root = Path(gettempdir(), uuid4().hex)
    return Directories(
        base=root,
        stack=root,
        bundles=root / "bundle",
        downloads=root / "download",
        files=root / "file",
        secrets=root / "secret",
        code=_PYTHON_DIR,
        data=root,
        run=root / "run",
        logs=root / "log",
        temp=root / "tmp",
    )


def _reset_runner_manager_and_start(task: TaskLog, runner_manager: TaskRunnerTestManager):
    runner_manager.reset()
    return runner_manager.start(task)


class TaskStarterOverride(dishka.Provider):
    @dishka.provide(scope=dishka.Scope.APP)
    def task_starter(self) -> TaskStarter:
        task_runner_manager = get_task_runner_manager()
        # reset is called for "natural" task reset, so duplicated start call will break only in unnatural cases
        return partial(_reset_runner_manager_and_start, runner_manager=task_runner_manager)


class DummySecretBackend(secrets.SecretsBackend):
    def write_all(self, secrets: secrets.ADCMSecrets) -> None:
        _ = secrets

    def read_all(
        self,
    ) -> Success[secrets.ADCMSecrets]:
        raise NotImplementedError("If you see it, please implement for tests")

    def read(self, secret: secrets.Secret) -> str:
        if secret == secrets.Secret.ANSIBLE_VAULT:
            return "ansible-secret-test"

        return secret.name


class EnvironmentOverride(dishka.Provider):
    scope = dishka.Scope.APP

    @provide
    def directories(self) -> Directories:
        return prepare_process_bound_directories()

    @provide
    def secrets_backend(self) -> secrets.SecretsBackend:
        return DummySecretBackend()

    @provide
    def adcm_version(self) -> CurrentADCMVersion:
        return CurrentADCMVersion(os.getenv("ADCM_VERSION", "2.0.0"))

    @provide
    def adcm_bundle_dir(self) -> ADCMBundleDir:
        return ADCMBundleDir(_PYTHON_DIR.parent / "conf" / "adcm")


class TaskRunnerOverride(dishka.Provider):
    scope = dishka.Scope.APP

    def __init__(self, *args, failed_job: FailedJobInfo | None | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._failed_job = failed_job

    @provide
    def failed_job(self) -> FailedJobInfo | None:
        return self._failed_job

    @provide
    def runner_settings(self, directories: Directories, consul: ConsulSettings) -> ExternalSettings:
        return ExternalSettings(
            adcm=ADCMSettings(code_root_dir=directories.code, run_dir=directories.run, log_dir=directories.logs),
            ansible=AnsibleSettings(ansible_secret_script=directories.code / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token="wow"),
            consul=consul,
        )

    job_repo = provide(JobImplRunnerMock, provides=JobRepoInterface)
    job_factory = provide(ExecutionTargetFactoryDummyMock, provides=ExecutionTargetFactoryI)

    @provide
    def job_processor(self, factory: ExecutionTargetFactoryI) -> JobProcessor:
        return JobProcessor(convert=factory)

    environment = provide(SubprocessRunnerMockEnvironment, provides=RunnerEnvironment)


class MockWithEnvProvider(dishka.Provider):
    scope = dishka.Scope.APP

    def __init__(self, *args, change_jobs: dict[int, JobImitator] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._change_jobs = change_jobs

    @provide
    def change_jobs(self) -> dict[int, JobImitator] | None:
        return self._change_jobs

    job_factory = provide(ETFMockWithEnvPreparation, provides=ExecutionTargetFactoryI)


def get_default_overridden_providers() -> tuple[dishka.Provider, ...]:
    return (
        *get_main_providers(),
        EnvironmentOverride(),
        TaskStarterOverride(),
        TaskRunnerOverride(),
    )


def make_default_dishka_container_for_tests() -> dishka.Container:
    providers = get_default_overridden_providers()

    return dishka.make_container(*providers)


class DishkaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        self.container = make_default_dishka_container_for_tests()

    def __call__(self, request):
        with self.container(scope=dishka.Scope.REQUEST) as request_container:
            request.container = request_container
            return self.get_response(request)
