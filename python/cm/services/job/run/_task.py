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

import logging

from core.types import PID
from jobs.services.concerns import distribute_concerns
from jobs.services.task import run_task_in_local_subprocess

from cm.models import ActionHostGroup, TaskLog

logger = logging.getLogger("adcm")


def start_task(task: TaskLog) -> PID:
    _distribute_concerns(task=task)
    return run_task_in_local_subprocess(task=task, command="start")


def restart_task(task: TaskLog) -> PID:
    _distribute_concerns(task=task)
    return run_task_in_local_subprocess(task=task, command="restart")


def _distribute_concerns(task: TaskLog) -> None:
    target = task.task_object
    if isinstance(target, ActionHostGroup):
        target = target.object

    distribute_concerns(task=task, target=target)
