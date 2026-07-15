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

from collections.abc import Callable, Generator, Iterable
from datetime import datetime
from functools import partial
from typing import Any, NamedTuple

from core.action import Job, ScriptType, Task
from core.cluster import ClusterService
from core.legacy.job.executors import ExecutionResult, Executor, ExecutorConfig
from core.legacy.job.runners import ExecutionTarget, ExternalSettings
from core.logs import LogsService
from core.scenarios.config import ConfigScenarios
from django.utils import timezone
from rbac.scenarios import RBACScenarios
from typing_extensions import Self
from use_cases.cluster.update import ResetBeforeUpgradeCluster
from use_cases.provider.update import ResetBeforeUpgradeProvider
from use_cases.transition.config import UpdateConfigurationFromJob

from cm.impl.job.repo import JobRepo
from cm.legacy.services.job.run import ExecutionTargetFactory
from cm.legacy.services.job.run.executors import InternalScriptResult


def do_nothing(*_, **__):
    return None


class FailedJobInfo(NamedTuple):
    position: int
    return_code: int = 1


class JobImitator(NamedTuple):
    call: Callable[[Executor], Any] = do_nothing
    return_code: int = 0
    use_call_return_code: bool = False


default_imitator = JobImitator()


# ExecutionTarget Factories


class ExecutionTargetFactoryDummyMock(ExecutionTargetFactory):
    def __init__(
        self,
        *,
        failed_job: FailedJobInfo | None = None,
        logs_service: LogsService,
        rbac_scenarios: RBACScenarios,
        reset_cluster_before_upgrade: ResetBeforeUpgradeCluster,
        reset_provider_before_upgrade: ResetBeforeUpgradeProvider,
        update_configuration_from_job: UpdateConfigurationFromJob,
        config_scenarios: ConfigScenarios,
        cluster_service: ClusterService,
    ):
        super().__init__(
            logs_service=logs_service,
            rbac_scenarios=rbac_scenarios,
            reset_cluster_before_upgrade=reset_cluster_before_upgrade,
            reset_provider_before_upgrade=reset_provider_before_upgrade,
            update_configuration_from_job=update_configuration_from_job,
            config_scenarios=config_scenarios,
            cluster_service=cluster_service,
        )

        self._failed_job = failed_job

    def __call__(
        self, task: Task, jobs: Iterable[Job], configuration: ExternalSettings
    ) -> Generator[ExecutionTarget, None, None]:
        _ = task
        for job_num, job in enumerate(jobs):
            work_dir = configuration.adcm.run_dir / str(job.id)

            if job.type == ScriptType.INTERNAL:
                internal_script_func = self._supported_internal_scripts[job.script]
                script = partial(internal_script_func, task=task, job=job)
                executor = InternalExecutorMock(config=ExecutorConfig(work_dir=work_dir), script=script)

            else:
                executor_kwargs = {}
                if self._failed_job is not None and job_num == self._failed_job.position:
                    executor_kwargs = {"return_code": self._failed_job.return_code}

                job_imitator = JobImitator(**executor_kwargs)
                executor = MockExecutor(
                    script_type=job.script,
                    imitator=job_imitator,
                    config=ExecutorConfig(work_dir=configuration.adcm.run_dir / str(job.id)),
                )

            yield ExecutionTarget(
                job=job,
                executor=executor,
                environment_builders=(),
                finalizers=(),
            )


class ETFMockWithEnvPreparation(ExecutionTargetFactory):
    def __init__(
        self,
        *,
        change_jobs: dict[int, JobImitator] | None = None,
        logs_service: LogsService,
        rbac_scenarios: RBACScenarios,
        reset_cluster_before_upgrade: ResetBeforeUpgradeCluster,
        reset_provider_before_upgrade: ResetBeforeUpgradeProvider,
        update_configuration_from_job: UpdateConfigurationFromJob,
        config_scenarios: ConfigScenarios,
        cluster_service: ClusterService,
    ):
        super().__init__(
            logs_service=logs_service,
            rbac_scenarios=rbac_scenarios,
            reset_cluster_before_upgrade=reset_cluster_before_upgrade,
            reset_provider_before_upgrade=reset_provider_before_upgrade,
            update_configuration_from_job=update_configuration_from_job,
            config_scenarios=config_scenarios,
            cluster_service=cluster_service,
        )

        self.imitators = change_jobs or {}
        self.default_imitator = default_imitator

    def __call__(
        self, task: Task, jobs: Iterable[Job], configuration: ExternalSettings
    ) -> Generator[ExecutionTarget, None, None]:
        for i, target in enumerate(super().__call__(task=task, jobs=jobs, configuration=configuration)):
            if target.job.type == ScriptType.INTERNAL:
                yield target
                continue

            imitator = self.imitators.get(i, self.default_imitator)
            executor = MockExecutor(
                script_type=target.executor.script_type,
                config=ExecutorConfig(work_dir=configuration.adcm.run_dir / str(target.job.id)),
                imitator=imitator,
            )

            yield ExecutionTarget(
                job=target.job,
                executor=executor,
                environment_builders=target.environment_builders,
                finalizers=target.finalizers,
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


class InternalExecutorMock(MockExecutor):
    script_type = "internal"

    def __init__(self, config: ExecutorConfig, script: Callable[[], InternalScriptResult]):
        super().__init__(config=config)
        self._script = script

    def execute(self) -> Self:
        script_result = self._script()
        self._result = ExecutionResult(code=script_result.code)
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
