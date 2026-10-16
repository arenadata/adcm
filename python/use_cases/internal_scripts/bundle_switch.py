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

from cm.impl.scenarios.bundle_switch import BundleSwitch
from cm.legacy.services.job.run.executors import InternalScriptResult
from cm.models import Cluster, Provider, TaskLog
from core.action import Task
from core.action.types import SimpleInternalScript
from core.types import JobID
from django.db.transaction import atomic
from rbac.roles import re_apply_policy_for_jobs

from use_cases.internal_scripts.common import build_result_message


@dataclass(slots=True)
class BundleSwitchInternalScript:
    bundle_switch: BundleSwitch

    @atomic()
    def do(self, task: Task, script: SimpleInternalScript, job_id: JobID) -> InternalScriptResult:
        _ = script, job_id

        task_ = TaskLog.objects.get(id=task.id)

        target = task_.task_object
        if not isinstance(target, Cluster | Provider):
            message = f"Task object: was given {type(target).__name__}, expected Cluster or Provider"
            raise RuntimeError(message)  # noqa: TRY004

        self.bundle_switch.do(target=target, upgrade=task_.action.upgrade)

        re_apply_policy_for_jobs(task=task_)

        result_message = build_result_message(
            script_name="bundle_switch",
            full_complete_message="the prototype is switched",
            with_updates=True,
        )
        return InternalScriptResult(code=0, message=result_message)
