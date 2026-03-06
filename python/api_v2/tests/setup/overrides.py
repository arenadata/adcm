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
from unittest.mock import patch

from application.di.containers import get_main_providers
from cm.models import TaskLog
from cm.tests.mocks.task_runner import (
    ExecutionTargetFactoryDummyMock,
    JobImplRunnerMock,
    SubprocessRunnerMockEnvironment,
)
from core.legacy.job.runners import ExecutionTargetFactoryI
from core.types import PID, TaskID
from use_cases.transition.job.schedule import TaskStarter
import dishka

_DEFAULT_ETF_MOCK = ExecutionTargetFactoryDummyMock()


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

    def run_launched_task(
        self, task_id: TaskID | None = None, execution_target_factory: ExecutionTargetFactoryI = _DEFAULT_ETF_MOCK
    ) -> None:
        task_id_ = self.expect_task_launched(task_id).id
        self.run_task(task_id=task_id_, execution_target_factory=execution_target_factory)

    def run_task(
        self,
        task_id: TaskID,
        execution_target_factory: ExecutionTargetFactoryI = _DEFAULT_ETF_MOCK,
    ) -> None:
        from cm.legacy.services.job.run import get_default_runner

        with patch("cm.legacy.services.job.run._impl._factory", new=execution_target_factory), patch(
            "cm.legacy.services.job.run._impl.SubprocessRunnerEnvironment", new=SubprocessRunnerMockEnvironment
        ), patch("cm.legacy.services.job.run._impl.JobRepoImpl", new=JobImplRunnerMock):
            runner = get_default_runner()

        runner.run(task_id)


@cache
def get_task_runner_manager() -> TaskRunnerTestManager:
    return TaskRunnerTestManager()


def _reset_runner_manager_and_start(task: TaskLog, runner_manager: TaskRunnerTestManager):
    runner_manager.reset()
    return runner_manager.start(task)


class TaskStarterOverride(dishka.Provider):
    @dishka.provide(scope=dishka.Scope.APP)
    def task_starter(self) -> TaskStarter:
        task_runner_manager = get_task_runner_manager()
        # reset is called for "natural" task reset, so duplicated start call will break only in unnatural cases
        return partial(_reset_runner_manager_and_start, runner_manager=task_runner_manager)


class DishkaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        providers = (
            *get_main_providers(),
            TaskStarterOverride(),
        )

        self.container = dishka.make_container(*providers)

    def __call__(self, request):
        with self.container(scope=dishka.Scope.REQUEST) as request_container:
            request.container = request_container
            return self.get_response(request)
