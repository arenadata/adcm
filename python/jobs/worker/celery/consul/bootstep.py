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
``ConsulListenerStep`` - worker :class:`~celery.bootsteps.StartStopStep` that
polls Consul KV for control/inspect commands targeted at the current worker,
executes them locally via Celery's ``Panel`` registry, writes the result
back to the response KV path and finally removes the original command.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from celery import bootsteps
from celery.utils.collections import AttributeDict
from celery.utils.functional import pass1
from celery.utils.nodenames import gethostname
from celery.worker import control as worker_control

from jobs.scheduler.logger import logger
from jobs.worker.celery.consul import settings as consul_settings
from jobs.worker.celery.consul.client import ConsulKVClient, get_consul_kv_client
from jobs.worker.celery.consul.control import Command, response_key


class ConsulListenerStep(bootsteps.StartStopStep):
    """
    Periodically consume commands from
    ``CONSUL_KV_COMMAND_PREFIX/<command_id>``.

    For every command directed at the current worker (either unscoped or
    explicitly listing ``hostname`` in ``destination``) the handler registered
    in :mod:`celery.worker.control`'s ``Panel`` is invoked; the return value
    is stored at
    ``CONSUL_KV_RESPONSE_PREFIX/<command_id>/<worker.hostname>`` and the
    original command key is removed so that it is not re-executed by another
    worker in the pool.
    """

    requires = {"celery.worker.components:Timer"}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.hostname = f"celery@{gethostname()}"
        self._tref = None

    def start(self, work_controller) -> None:
        if not consul_settings.is_enabled():
            logger.debug("Consul control transport disabled; ConsulListenerStep will not start.")
            return

        interval = consul_settings.CONSUL_KV_COMMAND_POLL_INTERVAL
        consumer = ConsulCommandConsumer(app=work_controller.app, hostname=self.hostname)

        self._tref = work_controller.timer.call_repeatedly(
            secs=interval,
            fun=consumer.poll_once,
        )
        logger.info(
            f"Consul control listener started at {self.hostname} "
            f"(interval={interval}s, prefix={consul_settings.CONSUL_KV_COMMAND_PREFIX})"
        )

    def stop(self, work_controller) -> None:
        _ = work_controller
        if self._tref is not None:
            self._tref.cancel()
            self._tref = None


class ConsulCommandConsumer:
    """
    Stateful helper used by :class:`ConsulListenerStep` to execute one
    poll iteration.
    """

    def __init__(self, *, app, hostname: str, client: ConsulKVClient | None = None) -> None:
        self._app = app
        self._hostname = hostname
        self._client = client or get_consul_kv_client()
        self._panel_state = _build_panel_state(app=app, hostname=hostname)

    def poll_once(self) -> None:
        prefix = consul_settings.normalize_prefix(consul_settings.CONSUL_KV_COMMAND_PREFIX or "")
        try:
            pairs = self._client.list_pairs(prefix)
        except Exception:  # noqa: BLE001
            logger.error("Failed to list Consul control commands")
            return

        for key, payload in pairs.items():
            self._handle_one(key=key, payload=payload)

    def _handle_one(self, *, key: str, payload: Any) -> None:
        try:
            if not isinstance(payload, dict):
                logger.warning(f"Skipping malformed Consul control command at {key!r}: {payload!r}")
                self._safe_delete(key)
                return

            command = Command.from_payload(payload)
        except (KeyError, ValueError, TypeError):
            logger.exception(f"Skipping unparsable Consul control command at {key!r}")
            self._safe_delete(key)
            return

        if not self._matches_destination(command.destination):
            # command is for other workers; leave it alone
            return

        result = self._execute(command)
        self._publish_response(command_id=command.id, result=result)
        self._safe_delete(key)

    def _matches_destination(self, destination: Iterable[str] | None) -> bool:
        if not destination:
            return True
        return self._hostname in destination

    def _execute(self, command: Command) -> dict[str, Any]:
        handler = worker_control.Panel.data.get(command.method)
        if handler is None:
            return {"error": f"No such control command: {command.method!r}"}

        try:
            return handler(self._panel_state, **command.arguments)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Consul control command {command.method!r} failed")
            return {"error": repr(exc)}

    def _publish_response(self, *, command_id: str, result: dict[str, Any]) -> None:
        key = response_key(command_id=command_id, hostname=self._hostname)
        try:
            self._client.put(key, result)
        except Exception:  # noqa: BLE001
            logger.error(f"Failed to publish Consul control response for command {command_id!r}")

    def _safe_delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception:  # noqa: BLE001
            logger.error(f"Failed to delete processed Consul control command {key!r}")


def _build_panel_state(*, app, hostname: str):
    """
    Construct a state object accepted by Celery ``Panel`` handlers.

    Celery's own :class:`~celery.worker.pidbox.Pidbox` builds a very similar
    ``AttributeDict`` for the mailbox listener; we reuse the same shape so
    that shipped control commands (``ping``, ``stats``, ``active``, ...) work
    unchanged when dispatched via Consul.
    """
    return AttributeDict(
        app=app,
        hostname=hostname,
        consumer=None,
        tset=pass1,
    )
