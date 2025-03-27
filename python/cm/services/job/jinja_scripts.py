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

from pathlib import Path
from typing import Generator

from core.bundle_alt.process import ScriptJinjaContext, parse_scripts_jinja
from core.job.types import JobSpec
from core.types import TaskID

from cm.errors import AdcmEx
from cm.models import (
    TaskLog,
)
from cm.services.bundle import BundlePathResolver, detect_relative_path_to_bundle_root
from cm.services.jinja_env import get_env_for_jinja_scripts
from cm.services.job.types import TaskMappingDelta
from cm.services.template import TemplateBuilder
from cm.utils import get_on_fail_states


def get_job_specs_from_template(
    task_id: TaskID, delta: TaskMappingDelta | None, feature_scripts_jinja: bool = False
) -> Generator[JobSpec, None, None]:
    task = TaskLog.objects.select_related("action", "action__prototype__bundle").get(pk=task_id)

    path_resolver = BundlePathResolver(bundle_hash=task.action.prototype.bundle.hash)
    scripts_jinja_file = path_resolver.resolve(task.action.scripts_jinja)
    template_builder = TemplateBuilder(
        template_path=scripts_jinja_file,
        context=get_env_for_jinja_scripts(task=task, delta=delta),
        bundle_path=path_resolver.bundle_root,
        error=AdcmEx(code="UNPROCESSABLE_ENTITY", msg="Can't render jinja template"),
    )

    if not template_builder.data:
        raise RuntimeError(f'Template "{scripts_jinja_file}" has no jobs')

    dir_with_jinja = scripts_jinja_file.parent.relative_to(path_resolver.bundle_root)

    if feature_scripts_jinja:
        context = ScriptJinjaContext(
            source_dir=dir_with_jinja, action_allow_to_terminate=task.action.allow_to_terminate
        )
        yield from parse_scripts_jinja(data=template_builder.data, context=context)
    else:
        yield from _get_job_specs(
            data=template_builder.data,
            template_dir=dir_with_jinja,
            action_allow_to_terminate=task.action.allow_to_terminate,
        )


def _get_job_specs(
    data: list[dict], template_dir: Path, action_allow_to_terminate: bool
) -> Generator[JobSpec, None, None]:
    for job in data:
        state_on_fail, multi_state_on_fail_set, multi_state_on_fail_unset = get_on_fail_states(config=job)
        yield JobSpec(
            name=job["name"],
            display_name=job.get("display_name", ""),
            script=str(detect_relative_path_to_bundle_root(source_file_dir=template_dir, raw_path=job["script"])),
            script_type=job["script_type"],
            allow_to_terminate=job.get("allow_to_terminate", action_allow_to_terminate),
            state_on_fail=state_on_fail,
            multi_state_on_fail_set=multi_state_on_fail_set,
            multi_state_on_fail_unset=multi_state_on_fail_unset,
            params=job.get("params", {}),
        )
