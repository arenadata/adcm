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

from cm.errors import AdcmEx
from core.action import Task
from core.types import ADCMCoreType, ClusterID, ObjectID


def build_result_message(
    script_name: str,
    full_complete_message: str,
    with_updates: bool,
    without_updates_message: str | None = None,
) -> str:
    base_template = "The script `{script_name}` completed successfully, {completed_info}."

    if with_updates or without_updates_message is None:
        complete_info = full_complete_message
    else:
        complete_info = f"but {without_updates_message} earlier"

    return base_template.format(script_name=script_name, completed_info=complete_info)


def cluster_id_of_task(task: Task, script_name: str) -> ClusterID | None:
    """The cluster a task's owner belongs to, `None` for an owner outside any cluster"""

    owner = task.owner
    if owner is None:
        raise AdcmEx(code="WRONG_OWNER", msg=f"Internal script `{script_name}` can't run in a task without an owner")

    if owner.type == ADCMCoreType.CLUSTER:
        return owner.id

    if owner.type in {ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}:
        cluster = owner.related_objects.cluster
        if cluster is None:
            raise RuntimeError("Task owner's cluster: was given None, expected an object")

        return cluster.id

    return None


def provider_id_of_task(task: Task) -> ObjectID | None:
    """The provider a task's owner is or belongs to, if any"""

    owner = task.owner
    if owner is None:
        return None

    if owner.type == ADCMCoreType.PROVIDER:
        return owner.id

    provider = owner.related_objects.provider
    return provider.id if provider else None
