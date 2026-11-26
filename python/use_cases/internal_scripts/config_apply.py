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

from dataclasses import asdict, dataclass

from cm.converters import CoreObject, core_type_to_model
from cm.errors import AdcmEx
from cm.legacy.services.job import context as context_m
from cm.legacy.services.job.run.executors import InternalScriptResult
from cm.models import ADCM
from core.action import ConfigApplyChangeEntry, Task
from core.action.types import ConfigApplyScript
from core.types import JobID

from use_cases.internal_scripts.common import build_result_message
from use_cases.transition.config import UpdateConfigurationFromJob, apply_config_changes


@dataclass(slots=True)
class ConfigApplyInternalScript:
    update_configuration_from_job: UpdateConfigurationFromJob

    def do(self, task: Task, script: ConfigApplyScript, job_id: JobID) -> InternalScriptResult:
        with_updates = False
        # are we going to allow to change one component from context of another?
        for change in script.params.changes:
            changing_object = _extract_apply_config_target(task=task, change=change)
            has_changed = apply_config_changes(
                job_id=job_id,
                db_object=changing_object,
                parameters=[asdict(parameter) for parameter in change.parameters],
                changes_description=f"{task.display_name} process update",
                update_configuration_from_job=self.update_configuration_from_job,
            )
            # if at least one change has been applied, the script is marked as completed with updates
            with_updates = has_changed or with_updates

        result_message = build_result_message(
            script_name="config_apply",
            full_complete_message="the configuration updates are done",
            without_updates_message="the configuration was updated",
            with_updates=with_updates,
        )
        return InternalScriptResult(code=0, message=result_message)


def _extract_apply_config_target(task: Task, change: ConfigApplyChangeEntry) -> ADCM | CoreObject:
    # in order to preserve single mechanism with adcm_config plugin.
    # Requires refactoring to move it common location with plugins
    from ansible_plugin.base import CoreObjectTargetDescription, VarsContextSection, _from_target_description
    from ansible_plugin.errors import PluginTargetDetectionError

    context = VarsContextSection.model_validate(context_m.get_run_context(task=task))
    target_description = CoreObjectTargetDescription.model_validate(change.object, from_attributes=True)

    try:
        target = _from_target_description(target_description, context)
    except PluginTargetDetectionError as e:
        raise AdcmEx(
            code="INTERNAL_SERVER_ERROR",
            msg=f"The configuration contains non-existing object of owner {change.object}",
        ) from e

    return core_type_to_model(core_type=target.type).objects.get(pk=target.id)
