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
from typing import Any, Callable, Collection, NamedTuple, TypeVar
import json

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    AnsibleJobContext,
    CallArguments,
    CallResult,
    PluginExecutorConfig,
)
from cm.models import JobLog
from cm.services.job.run._target_factories import prepare_ansible_job_config
from cm.services.job.run.repo import JobRepoImpl
from core.job.executors import Executor as JobExecutor
from core.job.runners import ADCMSettings, AnsibleSettings, ExternalSettings, IntegrationsSettings
from core.job.types import Job
from core.types import CoreObjectDescriptor
from django.conf import settings
import yaml

Executor = TypeVar("Executor", bound=ADCMAnsiblePluginExecutor)


class ADCMAnsiblePluginTestMixin:
    def prepare_executor(
        self, executor_type: type[Executor], call_arguments: dict | str, call_context: dict | JobLog | Job | int
    ) -> Executor:
        """
        Prepare plugin executor more or less like it will be created inside Ansible plugin call

        You can specify `call_arguments` as dict, then it'll be passed right into executor's init function
        or write it as plain yaml string (that'll be evaluated to dict) to "imitate" ansible plugin call description
        (note that it should be inner section of plugin (without name).
        If it is a string, it'll be parsed with `yaml` (so no ansible filters or environment will be there).

        `call_context` can be either a context dict (with `type` and `*_id` fields)
        or a job (`Job`, `JobLog` or job's id as `int`) based on which this function will build context.
        """

        arguments = call_arguments
        if isinstance(arguments, str):
            arguments = yaml.safe_load(arguments)

        context = call_context
        if not isinstance(call_context, dict):
            configuration = ExternalSettings(
                adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
                ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
                integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
            )

            job_id = call_context if isinstance(call_context, int) else call_context.id
            task_id = JobLog.objects.values_list("task_id", flat=True).get(id=job_id)

            job_ansible_config = prepare_ansible_job_config(
                task=JobRepoImpl.get_task(id=task_id), job=JobRepoImpl.get_job(id=job_id), configuration=configuration
            )
            context = job_ansible_config["context"]

        return executor_type(arguments=arguments, context=context)

    def build_executor_call(
        self,
        arguments: dict | str,
        executor_type: type[ADCMAnsiblePluginExecutor],
    ) -> Callable[[JobExecutor], Any]:
        def _executor_func(executor: JobExecutor) -> int:
            context = json.loads((executor._config.work_dir / "config.json").read_text())["context"]
            plugin_executor = self.prepare_executor(
                executor_type=executor_type, call_arguments=arguments, call_context=context
            )
            result = plugin_executor.execute()
            return 0 if result.error is None else 1

        return _executor_func


class PassedArguments(NamedTuple):
    targets: Collection[CoreObjectDescriptor]
    arguments: CallArguments
    context_owner: CoreObjectDescriptor
    context: AnsibleJobContext


def DummyExecutor(  # noqa: N802
    config: PluginExecutorConfig[CallArguments],
) -> type[ADCMAnsiblePluginExecutor[CallArguments, PassedArguments]]:
    class DummyExecutorWithConfig(ADCMAnsiblePluginExecutor):
        _config: PluginExecutorConfig[CallArguments] = config

        def __call__(
            self,
            targets: Collection[CoreObjectDescriptor],
            arguments: CallArguments,
            context_owner: CoreObjectDescriptor,
            context: AnsibleJobContext,
        ) -> CallResult[PassedArguments]:
            return CallResult(
                value=PassedArguments(
                    targets=targets, arguments=arguments, context_owner=context_owner, context=context
                ),
                changed=True,
                error=None,
            )

    return DummyExecutorWithConfig
