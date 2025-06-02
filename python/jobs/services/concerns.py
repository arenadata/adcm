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

from cm.converters import orm_object_to_core_descriptor
from cm.models import TaskLog
from cm.services.concern.distribution import distribute_concern_on_related_objects
from cm.services.concern.locks import create_task_flag_concern, create_task_lock_concern
from cm.services.job.run.repo import TaskTargetCoreObject
from cm.status_api import notify_about_new_concern


def distribute_concerns(task: TaskLog, target: TaskTargetCoreObject) -> None:
    # copied from cm.services.job.run._task._run_task

    create_concern = create_task_lock_concern if task.is_blocking else create_task_flag_concern
    concern_id = create_concern(task=task)
    objects_to_notify = distribute_concern_on_related_objects(
        owner=orm_object_to_core_descriptor(target), concern_id=concern_id
    )
    notify_about_new_concern(concern_id=concern_id, related_objects=objects_to_notify)

    if task.is_blocking:
        task.lock_id = concern_id
        task.save(update_fields=["lock_id"])
