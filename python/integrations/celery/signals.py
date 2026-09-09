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

"""
Celery signal handlers used by the ADCM worker process.

These have real side effects (closing DB connections around a prefork fork,
mutating global status-service URL state, wiring worker-only logging) that
only make sense for the process that IS the worker, so they are never
connected automatically on import. Call `install_for_worker()` once, from
the worker entrypoint only.
"""

from typing import NoReturn
import logging
import logging.config

from application.loggers import task_worker_logging_config_from_env
from celery.exceptions import WorkerShutdown
from celery.signals import celeryd_after_setup, worker_before_create_process, worker_init, worker_process_init
from cm.legacy.status_api import status_service_url
from core.result import is_fail
from django.db import connections

from integrations.celery.errors import JobFailedFlowError
from integrations.celery.external_status_service_url import ResolveExternalStatusServiceURL
from integrations.celery.pg.transport import discard_engines_inherited_from_fork

logger = logging.getLogger("worker.celery")


class StatusServiceUrlResolutionError(WorkerShutdown):
    ...


class JobFailedFlowErrFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        is_special_exc = record.exc_info and record.exc_info[0] == JobFailedFlowError
        return not is_special_exc


# Fork safety
#
# Neither psycopg connections nor SQLAlchemy engines are fork-safe: anything the
# worker parent has open when billiard forks a pool child is inherited by both,
# and two processes speaking through one socket interleave protocol replies
# (surfacing as errors like "the last operation didn't produce records (command
# status: COMMIT)"). Celery's built-in Django fixup covers only Django-project
# setups; this worker assembles its own app, so the same guarantees are made
# explicitly here.


def close_parent_connections_before_fork(**_) -> None:
    # In the parent, right before every pool fork (including replacement
    # children forked at runtime): bootstrap code and startup hooks use the ORM,
    # so a connection may be open. Close it so the child inherits no socket.
    # The parent's SQLAlchemy transport engine stays untouched: it is in active
    # use by the consumer, and the child discards its inherited copy instead.
    connections.close_all()


def close_inherited_connections_in_child(**_) -> None:
    # In each pool child, right after fork: drop everything inherited so the
    # child lazily opens connections of its own. Replacement children fork
    # after the parent's consumer has opened the transport, so the SQLAlchemy
    # engine cache is populated at fork time — and children publish to the
    # broker (chain links), so a stale cache would reuse the parent's sockets.
    connections.close_all()
    discard_engines_inherited_from_fork()


# Status service URL resolution


def setup_status_service_url(sender, **_) -> None:
    """Point ``status_api`` at the resolved external status service URL on worker start.

    Wired to ``worker_init``, not a bootstep: the prefork pool forks its
    children while the worker blueprint is being built, before any bootstep's
    ``start`` runs, so a URL set from a bootstep exists only in the main
    process and every pool child falls back to the internal URL. worker_init
    fires in the main process before the blueprint (and thus the pool) is
    created, so the resolved URL is inherited by every forked child.
    """
    resolver = sender.app.di_container.get(ResolveExternalStatusServiceURL)

    result = resolver.resolve()
    if is_fail(result):
        _refuse_to_start(result.value)

    status_service_url.set_external(result.value)
    logger.info("Worker status events will be sent to %s", result.value)


# Logging


def configure_logging(sender, instance, **__):
    # Kept on `celeryd_after_setup` rather than `setup_logging`: we don't want to suppress
    # Celery's own default logging setup, only add our handlers/filters on top of it.

    _ = sender
    _ = instance

    logging_config = task_worker_logging_config_from_env()

    logging.config.dictConfig(logging_config)

    # Need to add filter for our custom error that is used to break the celery chain flow.
    # Since it's not exactly exception, it shouldn't be shown to user.
    # We can include it in the logging config right away, but now I keep it separate for simplicity.
    filter_ = JobFailedFlowErrFilter(name="exc_filter")
    logging.getLogger("celery.app.trace").addFilter(filter_)


def install_for_worker() -> None:
    # dispatch deduplicates receivers, so repeated installation is harmless
    worker_before_create_process.connect(close_parent_connections_before_fork)
    worker_process_init.connect(close_inherited_connections_in_child)
    worker_init.connect(setup_status_service_url)
    celeryd_after_setup.connect(configure_logging)


def _refuse_to_start(reason: str) -> NoReturn:
    message = (
        f"Could not resolve external status service url: {reason}. "
        "The worker cannot report status events without it, refusing to start."
    )
    # worker_init fires before celery configures logging, so nothing is attached
    # to the logger tree yet and the record reaches stderr via logging's last
    # resort handler; the message is repeated by SystemExit on process exit
    logger.critical(message)

    raise StatusServiceUrlResolutionError(message)
