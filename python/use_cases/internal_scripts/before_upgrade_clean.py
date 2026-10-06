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

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import cast

from cm.legacy.services.job.run.executors import InternalScriptResult
from core.action import Task
from core.action.types import RichJob
from core.types import ADCMCoreType, ClusterObjectDesc, ProviderObjectDesc

from use_cases.cluster.update import ResetBeforeUpgradeCluster
from use_cases.internal_scripts.common import build_result_message
from use_cases.provider.update import ResetBeforeUpgradeProvider


@dataclass(slots=True)
class BeforeUpgradeCleanInternalScript:
    reset_cluster_before_upgrade: ResetBeforeUpgradeCluster
    reset_provider_before_upgrade: ResetBeforeUpgradeProvider

    def do(self, task: Task, job: RichJob) -> InternalScriptResult:
        _ = job

        if not task.owner:
            raise RuntimeError("misconfigured task runner: no owner")

        descriptor = task.owner.as_descriptor

        reset_before_upgrade: Callable[[], None]
        match descriptor.type:
            case ADCMCoreType.CLUSTER | ADCMCoreType.SERVICE | ADCMCoreType.COMPONENT if task.owner.related_objects:
                if descriptor.type == ADCMCoreType.CLUSTER:
                    cluster_id = descriptor.id
                else:
                    if not task.owner.related_objects.cluster:
                        raise RuntimeError("cluster is missing")

                    cluster_id = task.owner.related_objects.cluster.id

                reset_before_upgrade = partial(
                    self.reset_cluster_before_upgrade.do,
                    target=cast(ClusterObjectDesc, descriptor),
                    cluster_id=cluster_id,
                )

            case ADCMCoreType.PROVIDER | ADCMCoreType.HOST:
                reset_before_upgrade = partial(
                    self.reset_provider_before_upgrade.do, target=cast(ProviderObjectDesc, descriptor)
                )

            case _:
                raise RuntimeError("misconfigured task runner")

        reset_before_upgrade()

        result_message = build_result_message(
            script_name="before_upgrade_clean",
            full_complete_message='"before_upgrade" section has been cleared',
            with_updates=True,
        )
        return InternalScriptResult(code=0, message=result_message)
