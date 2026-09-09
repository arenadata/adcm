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

from datetime import datetime
import os
import logging

from cm.legacy import status_api
from cm.legacy.services.job.run.runners import EventNotifier, JobSequenceRunner, StatusServerInteractor
from cm.legacy.services.job.run.target_factories import ExecutionTargetFactory
from cm.legacy.services.status import notify
from core.action.scheduler import ProcessStarter
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
)
from core.secrets import Secret, SecretsBackend
from core.settings import Directories
from dishka import Provider, Scope, from_context, provide, provide_all
from django.utils import timezone
from integrations.local.scheduler import LocalProcessStarter
from use_cases.job.run import FinalizeTask, MarkTaskBroken, RunJob, SetTaskToRunning, StartTask


class SubprocessRunnerEnvironment:
    @property
    def pid(self) -> int:
        return os.getpid()

    def now(self) -> datetime:
        return timezone.now()


class TaskRunnerProvider(Provider):
    scope = Scope.APP

    @provide
    def logger(self) -> logging.Logger:
        return logging.getLogger("task-runner")

    @provide  # must be moved to environment
    def consul_settings(self) -> ConsulSettings:
        return ConsulSettings(
            url=os.getenv("CONSUL_URL"),
            datacenter=os.getenv("CONSUL_DATACENTER"),
            cacert_file=os.getenv("CONSUL_CACERT_FILE"),
        )

    @provide
    def runner_settings(
        self, directories: Directories, secrets_backend: SecretsBackend, consul: ConsulSettings
    ) -> ExternalSettings:
        status_service_token = secrets_backend.read(Secret.STATUS_CHECKER_STATUS_SERVICE_TOKEN)

        return ExternalSettings(
            adcm=ADCMSettings(code_root_dir=directories.code, run_dir=directories.run, log_dir=directories.logs),
            ansible=AnsibleSettings(ansible_secret_script=directories.code / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=status_service_token),
            consul=consul,
        )

    @provide
    def notifier(self) -> EventNotifier:
        return status_api

    @provide
    def status_server(self) -> StatusServerInteractor:
        return notify

    job_factory = provide(ExecutionTargetFactory, provides=ExecutionTargetFactoryI)
    job_filter = from_context(JobFilterPredicate)
    job_processor = provide(JobProcessor)

    environment = provide(SubprocessRunnerEnvironment, provides=RunnerEnvironment)

    runner = provide(JobSequenceRunner, provides=TaskRunner)


class JobUseCaseProvider(Provider):
    scope = Scope.APP

    task_runner_steps = provide_all(SetTaskToRunning, RunJob, FinalizeTask, MarkTaskBroken, StartTask)
    process_starter = provide(LocalProcessStarter, provides=ProcessStarter)
