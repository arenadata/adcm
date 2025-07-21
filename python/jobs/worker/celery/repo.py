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

from datetime import datetime

from celery.backends.database import SessionManager
from django.db import connection
from sqlalchemy import create_engine

from jobs.scheduler._types import CELERY_RUNNING_STATES, UTC, CeleryTaskState
from jobs.scheduler.logger import logger
from jobs.worker.celery import settings
from jobs.worker.celery.models import Base, DBTables


def write_heartbeat(hostname) -> None:
    now = datetime.now(tz=UTC)
    sql = f"""
    INSERT INTO {DBTables.heartbeat} (hostname, timestamp)
    VALUES ('{hostname}', '{now}')
    ON CONFLICT (hostname) DO UPDATE
    SET timestamp = EXCLUDED.timestamp;
    """  # noqa: S608

    with connection.cursor() as cursor:
        cursor.execute(sql)


def retrieve_running_worker_tasks(hostname: str) -> set[int]:
    _running_states = ", ".join(f"'{status.value}'" for status in CELERY_RUNNING_STATES)
    condition = f"status IN ({_running_states}) AND worker = '{hostname}'"

    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {DBTables.taskmeta} WHERE {condition};")  # noqa: S608
        rows = cursor.fetchall()

    return {r[0] for r in rows}


def retrieve_alive_workers(threshold: datetime) -> set[str]:
    sql = f"SELECT DISTINCT hostname FROM {DBTables.heartbeat} WHERE timestamp >= '{threshold}'"  # noqa: S608

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    return {r[0] for r in rows}


def update_worker_tasks(ids: set[int], status: CeleryTaskState) -> None:
    ids = ", ".join(str(id_) for id_ in ids)

    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {DBTables.taskmeta} SET status = '{status}' WHERE id IN ({ids});"  # noqa: S608
        )


def _init_builtin_tables() -> None:
    session = SessionManager()
    engine = session.get_engine(settings.db_url)
    session.prepare_models(engine)

    logger.debug("Worker builtin tables initialized")


def _init_custom_tables() -> None:
    engine = create_engine(url=settings.db_url)
    Base.metadata.create_all(engine, checkfirst=True)

    logger.debug("Worker custom tables initialized")


def init_tables() -> None:
    _init_builtin_tables()
    _init_custom_tables()
