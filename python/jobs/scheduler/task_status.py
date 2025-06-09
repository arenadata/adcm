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

from contextlib import suppress
from functools import wraps
import logging

from cm.status_api import send_task_status_update_event
from core.job.dto import TaskUpdateDTO
from core.job.types import ExecutionStatus

logger = logging.getLogger("job_scheduler")


def set_status_on_success(status: ExecutionStatus):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = kwargs["task_id"]
            job_repo = kwargs["job_repo"]

            res = func(*args, **kwargs)
            job_repo.update_task(id=task_id, data=TaskUpdateDTO(status=status))
            with suppress(Exception):
                send_task_status_update_event(task_id=task_id, status=status.value)
            return res

        return wrapper

    return decorator


def set_status_on_fail(
    status: ExecutionStatus, errors: type[Exception] | tuple[type[Exception]], return_: bool = False
):
    if not isinstance(errors, tuple):
        errors = (errors,)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = kwargs["task_id"]
            job_repo = kwargs["job_repo"]

            try:
                return func(*args, **kwargs)
            except errors:
                job_repo.update_task(id=task_id, data=TaskUpdateDTO(status=status))
                with suppress(Exception):
                    send_task_status_update_event(task_id=task_id, status=status.value)
                logger.exception(f"Task #{task_id} is {status}")
                return return_

        return wrapper

    return decorator
