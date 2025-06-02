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

from cm.models import Action, TaskLog
from core.types import ActionID, TaskID


def retrieve_task_orm(task_id: TaskID) -> TaskLog:
    return TaskLog.objects.get(id=task_id)


def retrieve_action_orm(action_id: ActionID) -> Action:
    return Action.objects.get(id=action_id)
