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
Celery ``Control`` / ``Inspect`` replacements that use Consul KV as the
command/response transport.

Control flow
------------

On the caller (Django / scheduler) side:

    >>> app.control.broadcast("ping")
    # 1. allocate a fresh ``command_id`` (uuid4)
    # 2. PUT command payload at
    #        CONSUL_KV_COMMAND_PREFIX/<command_id>
    # 3. poll responses under
    #        CONSUL_KV_RESPONSE_PREFIX/<command_id>/<worker.hostname>
    #    every ``CONSUL_KV_RESPONSE_POLL_INTERVAL`` seconds until either
    #    all alive workers have responded or the timeout elapsed.
    # 4. return per-worker results

"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from functools import cached_property
from time import monotonic, sleep
from typing import Any, Iterable
from uuid import uuid4

from celery.app.control import Control, Inspect

from jobs.worker.celery.consul import settings as consul_settings
from jobs.worker.celery.consul.client import ConsulKVClient, get_consul_kv_client

DEFAULT_TIMEOUT = 1.0


@dataclass(frozen=True)
class Command:
    """A control/inspect command published to Consul KV.

    The worker bootstep reads instances of this dataclass from
    ``CONSUL_KV_COMMAND_PREFIX/<id>`` and executes them locally.
    """

    id: str
    method: str
    arguments: dict[str, Any]
    destination: tuple[str, ...] | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "method": self.method,
            "arguments": dict(self.arguments),
            "destination": list(self.destination) if self.destination else None,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Command:
        dest = payload.get("destination")
        return cls(
            id=str(payload["id"]),
            method=str(payload["method"]),
            arguments=dict(payload.get("arguments") or {}),
            destination=tuple(dest) if dest else None,
        )


class ConsulControl(Control):
    """Celery :class:`Control` replacement that broadcasts via Consul KV."""

    @cached_property
    def inspect(self):
        """Return a :class:`ConsulInspect` bound to this app."""
        return self.app.subclass_with_self(ConsulInspect, reverse="control.inspect")

    # Celery's Control exposes ``broadcast`` as the single entry point used
    # by revoke/ping/rate_limit/... We override it so that every control
    # command is routed through Consul instead of the Kombu mailbox.
    def broadcast(  # noqa: PLR0913
        self,
        command: str,
        arguments: dict[str, Any] | None = None,
        destination: Iterable[str] | None = None,
        connection=None,  # noqa: ARG002
        reply: bool = False,
        timeout: float | None = None,
        limit: int | None = None,
        callback=None,  # noqa: ARG002
        channel=None,  # noqa: ARG002
        pattern=None,  # noqa: ARG002
        matcher=None,  # noqa: ARG002
        **extra_kwargs,  # noqa: ARG002
    ):
        publisher = ConsulCommandPublisher(app=self.app, client=get_consul_kv_client())
        return publisher.send(
            method=command,
            arguments=arguments or {},
            destination=tuple(destination) if destination else None,
            reply=reply,
            timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
            limit=limit,
        )


class ConsulInspect(Inspect):
    """Inspect implementation that delegates to :class:`ConsulControl`."""

    def _request(self, command, **arguments):
        return self.app.control.broadcast(
            command,
            arguments=arguments,
            destination=self.destination,
            timeout=self.timeout if self.timeout is not None else DEFAULT_TIMEOUT,
            reply=True,
            limit=self.limit,
        )


class ConsulCommandPublisher:
    """
    Publishes a command to Consul KV and optionally collects per-worker
    responses.
    """

    def __init__(self, *, app, client: ConsulKVClient) -> None:
        self._app = app
        self._client = client

    def send(
        self,
        *,
        method: str,
        arguments: dict[str, Any],
        destination: tuple[str, ...] | None,
        reply: bool,
        timeout: float,
        limit: int | None,
    ) -> list[dict[str, Any]] | None:
        command = Command(
            id=uuid4().hex,
            method=method,
            arguments=arguments,
            destination=destination,
        )

        command_key = _command_key(command.id)
        self._client.put(command_key, command.to_payload())

        if not reply:
            return None

        try:
            return self._collect_responses(
                command_id=command.id,
                destination=destination,
                timeout=timeout,
                limit=limit,
            )
        finally:
            self._cleanup(command_id=command.id, command_key=command_key)

    def _collect_responses(
        self,
        *,
        command_id: str,
        destination: tuple[str, ...] | None,
        timeout: float,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        response_prefix = _response_prefix(command_id)
        expected = set(destination) if destination else None
        interval = consul_settings.CONSUL_KV_RESPONSE_POLL_INTERVAL

        deadline = monotonic() + max(timeout, 0.0)
        seen: dict[str, Any] = {}

        while True:
            for full_key, value in self._client.list_pairs(response_prefix).items():
                hostname = full_key.rsplit("/", 1)[-1]
                seen[hostname] = value

            if expected is not None and expected.issubset(seen):
                break
            if limit is not None and len(seen) >= limit:
                break
            if monotonic() >= deadline:
                break

            sleep(interval)

        return [{hostname: value} for hostname, value in seen.items()]

    def _cleanup(self, *, command_id: str, command_key: str) -> None:
        # Responses are removed after collection so that stale data does not
        # leak between calls; the command key is deleted only as a safety net
        # (the worker normally deletes it right after consuming).
        for key, recurse in ((_response_prefix(command_id), True), (command_key, False)):
            with suppress(Exception):
                self._client.delete(key, recurse=recurse)


def _command_key(command_id: str) -> str:
    prefix = consul_settings.normalize_prefix(consul_settings.CONSUL_KV_COMMAND_PREFIX or "")
    return f"{prefix}{command_id}"


def _response_prefix(command_id: str) -> str:
    prefix = consul_settings.normalize_prefix(consul_settings.CONSUL_KV_RESPONSE_PREFIX or "")
    return f"{prefix}{command_id}/"


def response_key(command_id: str, hostname: str) -> str:
    """Return the response KV path for ``(command_id, hostname)`` pair."""
    return f"{_response_prefix(command_id)}{hostname}"
