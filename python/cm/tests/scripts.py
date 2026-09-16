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

"""Helpers for seeding and reading actions' execution plans in tests"""

from collections.abc import Iterable

from core.action.job import JobShortFilter
from core.action.operations import flatten_execution_plan, to_rich_jobs
from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    JobDetails,
    JobSpecV1,
    RichJob,
    ScriptSpec,
    ScriptType,
)
from core.spec.types import FullSpecKey
from core.types import Names, TaskID

from cm.impl.common.execution_plan import dump_execution_plan, parse_execution_plan
from cm.impl.job.repo import JobRepo
from cm.models import Action


def build_script_spec(
    key: str,
    name: str,
    *,
    display_name: str = "",
    path: str = "script.yaml",
    terminatable: bool = False,
    **params,
) -> ScriptSpec:
    """Build an ansible script node, which is what most tests need to have a job at all"""

    return ScriptSpec(
        key=FullSpecKey(key),
        names=Names(internal=name, display=display_name),
        script=AnsibleScript(type=ScriptType.ANSIBLE, path=path, params=AnsibleScriptParams(**params)),
        details=JobDetails(terminatable=terminatable),
    )


def build_plan(*scripts: ScriptSpec) -> dict:
    """Build a plan in the shape it is stored in, envelope included"""

    return dump_execution_plan(JobSpecV1.from_scripts(*scripts))


def read_plan_scripts(actions: Iterable[Action]) -> list[ScriptSpec]:
    """Read scripts of the given actions in their declaration order, plans of all actions chained"""

    return [
        script_spec
        for stored in actions.values_list("scripts", flat=True)
        if stored
        for script_spec in parse_execution_plan(stored).scripts.values()
    ]


def names_with_params(scripts: Iterable[ScriptSpec]) -> list[tuple[str, dict]]:
    """Pair each script's own name with its params, the shape most upload assertions are written in"""

    return [(script.names.internal, script.script.params.model_dump()) for script in scripts]


def retrieve_rich_jobs(task_id: TaskID) -> tuple[RichJob, ...]:
    """A task's jobs paired with their plan nodes, in the order the plan runs them"""

    repo = JobRepo()

    plan = repo.get_execution_plan(task_id=task_id)
    task_jobs = repo.find_jobs_short(JobShortFilter(task_ids=[task_id]))
    jobs_by_key = to_rich_jobs(spec=plan, jobs=task_jobs)

    return tuple(jobs_by_key[key] for key in flatten_execution_plan(plan))
