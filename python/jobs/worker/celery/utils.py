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

from datetime import datetime, timedelta

from celery import Celery, bootsteps
from celery.utils.nodenames import gethostname

from jobs.scheduler._types import UTC, CeleryTaskState
from jobs.scheduler.logger import logger
from jobs.worker.celery import custom_settings, repo
from jobs.worker.celery.models import DBTables


class CustomWorkerStep(bootsteps.StartStopStep):
    """
    Modifies worker on start behaviour:
      - creates db tables if not exists
      - sets final status for stale tasks
      - starts custom db-driven heartbeat
    """

    requires = {"celery.worker.components:Timer"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hostname = f"celery@{gethostname()}"

    def start(self, work_controller):
        repo.init_tables()
        self._update_taskmeta_table()
        self._start_heartbeat(work_controller=work_controller)

    def _update_taskmeta_table(self) -> None:
        final_status = CeleryTaskState.FAILURE

        to_update = repo.retrieve_running_worker_tasks(hostname=self.hostname)
        if to_update:
            repo.update_worker_tasks(ids=to_update, status=final_status)

        logger.debug(
            f"Table {DBTables.taskmeta} updated: ({len(to_update)}) rows affected. "
            f"Set {final_status} status to tasks of {self.hostname} worker."
        )

    def _start_heartbeat(self, work_controller) -> None:
        work_controller.timer.call_repeatedly(
            secs=custom_settings.JOB_WORKER_CELERY_HEARTBEAT_INTERVAL,
            fun=repo.write_heartbeat,
            args=(self.hostname,),
        )

        logger.debug(f"DB heartbeat started at {self.hostname} worker.")


class InspectionMixin:
    _interval = timedelta(seconds=2 * custom_settings.JOB_WORKER_CELERY_HEARTBEAT_INTERVAL)

    def ping(self) -> set[str]:
        """
        Returns set of alive (there are timestamps not further than `2 * heartbeat_interval` seconds) celery workers.
        """
        threshold = datetime.now(tz=UTC) - self._interval

        return repo.retrieve_alive_workers(threshold=threshold)


class CustomCelery(Celery, InspectionMixin):
    pass
