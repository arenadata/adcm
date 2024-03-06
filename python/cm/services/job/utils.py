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

from dataclasses import dataclass
from pathlib import Path

from core.types import ObjectID
from django.conf import settings
from django.utils.functional import cached_property
from pydantic import Json

from cm.models import (
    Action,
    JobLog,
    TaskLog,
)
from cm.services.types import ADCMEntityType


@dataclass
class JobScope:
    job_id: ObjectID
    object: ADCMEntityType

    @cached_property
    def task(self) -> TaskLog:
        return TaskLog.objects.select_related("action", "action__prototype", "action__prototype__bundle").get(
            pk=self.job.task_id
        )

    @cached_property
    def job(self) -> JobLog:
        return JobLog.objects.get(pk=self.job_id)

    @cached_property
    def hosts(self) -> Json:
        return self.task.hosts or None

    @cached_property
    def config(self) -> Json:
        return self.task.config or None

    @cached_property
    def action(self) -> Action | None:
        return self.task.action


def get_script_path(action: Action, job: JobLog | None) -> str:
    # fixme remove `if` here.
    #  currently left for "backward compatibility", but actually script should always be set for job
    #  and job should always be passed in here
    script = job.script if job else action.script

    relative_path_part = "./"
    if script.startswith(relative_path_part):
        script = Path(action.prototype.path, script.lstrip(relative_path_part))

    return str(Path(get_bundle_root(action=action), action.prototype.bundle.hash, script))


def get_bundle_root(action: Action) -> str:
    if action.prototype.type == "adcm":
        return str(Path(settings.BASE_DIR, "conf"))

    return str(settings.BUNDLE_DIR)
