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

from cm.models import TaskLog
from cm.utils import get_env_with_venv_path
from core.types import PID
from django.conf import settings

logger = logging.getLogger("job_scheduler")


def run_task_in_local_subprocess(task: TaskLog, command: Literal["start", "restart"]) -> PID:
    err_file = open(  # noqa: SIM115
        Path(settings.LOG_DIR, "task_runner.err"), "a+", encoding="utf-8"
    )

    cmd = [
        str(settings.CODE_DIR / "task_runner.py"),
        command,
        str(task.pk),
    ]
    logger.debug(f"Task #{task.id} run cmd: {' '.join(cmd)}")
    proc = subprocess.Popen(  # noqa: SIM115
        args=cmd, stderr=err_file, env=get_env_with_venv_path(venv=task.action.venv)
    )

    return proc.pid
