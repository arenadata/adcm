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

from cm.hierarchy import Tree
from cm.issue import lock_affected_objects
from cm.models import ActionHostGroup, TaskLog
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
    tree = Tree(obj=owner)
    affected_objs = (node.value for node in tree.get_all_affected(node=tree.built_from))
    lock_affected_objects(task=task, objects=affected_objs, lock_target=owner)

    err_file = open(  # noqa: SIM115
        Path(settings.LOG_DIR, "task_runner.err"),
        "a+",
        encoding=settings.ENCODING_UTF_8,
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
