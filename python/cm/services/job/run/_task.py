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
from typing import Literal
import logging
import subprocess

from django.conf import settings

from cm.converters import orm_object_to_core_descriptor
from cm.models import ActionHostGroup, TaskLog
from cm.services.concern.distribution import distribute_concern_on_related_objects
from cm.services.concern.locks import create_task_flag_concern, create_task_lock_concern
from cm.status_api import notify_about_new_concern
from cm.utils import get_env_with_venv_path

logger = logging.getLogger("adcm")


def run_task(task: TaskLog) -> None:
    _run_task(task=task, command="start")


def restart_task(task: TaskLog) -> None:
    _run_task(task=task, command="restart")


def _run_task(task: TaskLog, command: Literal["start", "restart"]):
    owner = task.task_object
    if isinstance(owner, ActionHostGroup):
        owner = owner.object

    create_concern = create_task_lock_concern if task.is_blocking else create_task_flag_concern
    concern_id = create_concern(task=task)
    objects_to_notify = distribute_concern_on_related_objects(
        owner=orm_object_to_core_descriptor(owner), concern_id=concern_id
    )
    notify_about_new_concern(concern_id=concern_id, related_objects=objects_to_notify)

    if task.is_blocking:
        task.lock_id = concern_id
        task.save(update_fields=["lock_id"])

    err_file = open(  # noqa: SIM115
        Path(settings.LOG_DIR, "task_runner.err"), "a+", encoding="utf-8"
    )

    cmd = [
        str(settings.CODE_DIR / "task_runner.py"),
        command,
        str(task.pk),
    ]
    logger.info("task run cmd: %s", " ".join(cmd))
    proc = subprocess.Popen(  # noqa: SIM115
        args=cmd, stderr=err_file, env=get_env_with_venv_path(venv=task.action.venv)
    )
    logger.info("task run #%s, python process %s", task.pk, proc.pid)
