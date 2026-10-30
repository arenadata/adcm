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

"""
Utilities for concurrency scenarios: their branches as plain calls,
to run them with `run_concurrently` or one by one.

What a branch calls is declared by test: plugin executor with its arguments (`plugin`)
or internal script with its params (`internal_script`), neither playbooks nor task runner are involved.
Task of an action is used only as a source of what branches get at runtime:
the task itself and a job per branch (e.g. config changes are bound to job, `adcm_hc` checks action of job's task).

Every call is prepared the way `RunJob` does it (related configs of job are created beforehand), then:
- plugin executor is prepared by `prepare_plugin_executor` as in plugin tests, with job's config as ansible variables
  (what ansible reads from `config.json`), and called outside of any transaction,
  since in production plugin is called by separate ansible process;
- internal script is called in a transaction, as `RunJob` does.

Caveats:
- every call opens its own DI scope, so it may be run in any thread;
- calls raise errors of plugins and internal scripts, rather than return them as job's return code.
"""

from collections.abc import Callable, Sequence
from typing import Any, Final, Protocol, TypeVar

from ansible_plugin.base import ADCMAnsiblePluginExecutor
from cm.impl.job.repo import JobRepo
from cm.legacy.services.job.run import create_related_configs
from cm.legacy.services.job.run.executors import InternalScriptResult
from cm.tests.scripts import retrieve_rich_jobs
from core.action import Task
from core.action.types import RichJob
from core.config import ConfigRepoI
from core.types import JobID, TaskID
from django.db.transaction import atomic
from tests.ansible import prepare_plugin_executor, prepare_plugin_runtime_vars
import dishka

ScriptT = TypeVar("ScriptT", contravariant=True)

BranchCall = Callable[[], Any]
# what branch calls, bound to the task and the job of the branch by `prepare_script_group`
Branch = Callable[[Task, RichJob, dishka.Container], BranchCall]


class InternalScriptRunner(Protocol[ScriptT]):
    def do(self, task: Task, script: ScriptT, job_id: JobID) -> InternalScriptResult: ...


def start_branch() -> None:
    """
    Called by every branch before it does anything.

    It's a generic sync point for `run_concurrently`:
    it guarantees that branches overlap, but not that they read before each other's writes.
    """


BRANCH_START: Final = f"{__name__}.{start_branch.__name__}"


def plugin(executor_type: type[ADCMAnsiblePluginExecutor], arguments: dict) -> Branch:
    """Branch calling plugin executor the same way plugin tests do, `arguments` are the ones plugin gets in playbook"""

    def prepare(task: Task, job: RichJob, container: dishka.Container) -> BranchCall:
        _ = task

        with container() as scope:
            runtime_vars = prepare_plugin_runtime_vars(job=job, container=scope)

        def call_plugin() -> Any:
            start_branch()

            with container() as scope:
                executor = prepare_plugin_executor(
                    executor_type=executor_type, call_arguments=arguments, call_context=runtime_vars, container=scope
                )
                result = executor.execute()

            if result.error is not None:
                raise result.error

            return result

        return call_plugin

    return prepare


def internal_script(script_type: type[InternalScriptRunner[ScriptT]], script: ScriptT) -> Branch:
    """Branch calling internal script (e.g. `ConfigApplyInternalScript`) with `script` holding its params"""

    def prepare(task: Task, job: RichJob, container: dishka.Container) -> BranchCall:
        def call_internal_script() -> InternalScriptResult:
            start_branch()

            with container() as scope, atomic():
                result = scope.get(script_type).do(task=task, script=script, job_id=job.runtime.id)

            if result.code != 0:
                message = f"Internal script {script_type.__name__} failed: {result.message}"
                raise RuntimeError(message)

            return result

        return call_internal_script

    return prepare


def prepare_script_group(
    task_id: TaskID, container: dishka.Container, branches: Sequence[Branch]
) -> tuple[BranchCall, ...]:
    """Calls of script group made of `branches`, each one bound to its own job of the task, in order of task's plan"""

    task = JobRepo().get_task(id=task_id)
    jobs = retrieve_rich_jobs(task_id=task_id)
    if len(jobs) < len(branches):
        message = f"Task #{task_id} has {len(jobs)} jobs, it's not enough for {len(branches)} branches"
        raise ValueError(message)

    jobs = jobs[: len(branches)]

    # `RunJob` saves ids of configs of task owner's hierarchy to every job before it's run:
    # config changes (`adcm_config`, `config_apply`) update them and fail if they aren't saved
    with container() as scope:
        config_repo = scope.get(ConfigRepoI)
        for job in jobs:
            create_related_configs(job_id=job.runtime.id, owner=task.owner, config_repo=config_repo)  # pyright: ignore[reportArgumentType]

    return tuple(branch(task, job, container) for branch, job in zip(branches, jobs, strict=True))
