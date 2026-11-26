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

from collections.abc import Collection
from typing import Any, NamedTuple, TypeVar

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    CallArguments,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
)
from cm.impl.job.repo import JobRepo
from cm.legacy.services.job.run.target_factories import prepare_ansible_job_config
from cm.models import JobLog
from core.action.job import JobShortFilter
from core.action.operations import to_rich_job
from core.action.types import RichJob
from core.config import ConfigService
from core.legacy.job.runners import ExternalSettings
from core.types import CoreObjectDescriptor, JobID
import yaml
import dishka

Executor = TypeVar("Executor", bound=ADCMAnsiblePluginExecutor)


class PassedArguments(NamedTuple):
    targets: Collection[CoreObjectDescriptor]
    arguments: CallArguments
    runtime: RuntimeEnvironment


def DummyExecutor(  # noqa: N802
    config: PluginExecutorConfig[CallArguments],
) -> type[ADCMAnsiblePluginExecutor[CallArguments, PassedArguments]]:
    class DummyExecutorWithConfig(ADCMAnsiblePluginExecutor):
        _config: PluginExecutorConfig[CallArguments] = config

        def __call__(
            self, targets: Collection[CoreObjectDescriptor], arguments: CallArguments, runtime: RuntimeEnvironment
        ) -> CallResult[PassedArguments]:
            return CallResult(
                value=PassedArguments(targets=targets, arguments=arguments, runtime=runtime),
                changed=True,
                error=None,
            )

    return DummyExecutorWithConfig


def prepare_plugin_runtime_vars(job: RichJob | JobLog | JobID, container: dishka.Container) -> dict[str, Any]:
    """
    What ansible gets as extra vars from job's `config.json`: plugin executors read `context` and `job` of it.

    Related configs of the job should be created beforehand, if plugin changes configs.
    """

    match job:
        case int():
            job_id = job
        case RichJob():
            job_id = job.runtime.id
        case _:
            job_id = job.id

    repo = JobRepo()
    task_id = JobLog.objects.values_list("task_id", flat=True).get(id=job_id)
    plan = repo.get_execution_plan(task_id=task_id)
    found_job, *_ = repo.find_jobs_short(JobShortFilter(ids=[job_id]))

    return prepare_ansible_job_config(
        task=repo.get_task(id=task_id),
        job=to_rich_job(spec=plan, job=found_job),
        configuration=container.get(ExternalSettings),
        config_service=container.get(ConfigService),
    )


def prepare_plugin_executor(
    executor_type: type[Executor],
    call_arguments: dict | str,
    call_context: dict | RichJob | JobLog | JobID,
    container: dishka.Container,
) -> Executor:
    """
    Prepare plugin executor more or less like it will be created inside Ansible plugin call

    You can specify `call_arguments` as dict, then it'll be passed right into executor's init function
    or write it as plain yaml string (that'll be evaluated to dict) to "imitate" ansible plugin call description
    (note that it should be inner section of plugin (without name).
    If it is a string, it'll be parsed with `yaml` (so no ansible filters or environment will be there).

    `call_context` can be either runtime vars (a dict with `context` and `job` sections,
    see `prepare_plugin_runtime_vars`) or a job (`RichJob`, `JobLog` or job's id as `int`)
    based on which this function will build them.

    `container` is used by executor during the call, so it should stay open until the call is finished.
    """

    arguments = yaml.safe_load(call_arguments) if isinstance(call_arguments, str) else call_arguments
    runtime_vars = (
        call_context
        if isinstance(call_context, dict)
        else prepare_plugin_runtime_vars(job=call_context, container=container)
    )

    return executor_type(arguments=arguments, runtime_vars=runtime_vars, container=container)
