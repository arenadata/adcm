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
psycopg3 ``LISTEN``/``NOTIFY`` connection used for fanout.

This is the transport's equivalent of redis' ``subclient``: a single
long-lived, autocommit connection dedicated to pub/sub. It never runs queue
storage queries (those go through the SQLAlchemy engine) so its socket can be
handed to kombu's event loop and stay readable exactly when a broadcast
arrives.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import NamedTuple
import re

from psycopg import sql
from sqlalchemy.engine import make_url
import psycopg

# Postgres identifier rules for channel names. NOTIFY channel names are plain
# identifiers, so we defensively reject anything that would need quoting rather
# than risk an injection point on the fanout path.
_SAFE_CHANNEL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# PostgreSQL caps a NOTIFY payload at 8000 bytes. Fanout (pidbox) commands are
# small, but we assert on it so an oversized broadcast fails loudly instead of
# being silently truncated by the server.
MAX_NOTIFY_PAYLOAD = 8000


class Notification(NamedTuple):
    channel: str
    payload: str


def sqlalchemy_url_to_dsn(url: str) -> str:
    """Convert a SQLAlchemy URL (``postgresql+psycopg://...``) to a libpq DSN."""
    parsed = make_url(url)
    # drop the driver part of the dialect (``postgresql+psycopg`` -> ``postgresql``)
    return parsed.set(drivername=parsed.get_backend_name()).render_as_string(hide_password=False)


class ListenConnection:
    """Owns one psycopg connection dedicated to ``LISTEN``/``NOTIFY``."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: psycopg.Connection | None = None
        self._channels: set[str] = set()

    @property
    def connection(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._dsn, autocommit=True)
            # re-arm subscriptions after a reconnect
            for channel in self._channels:
                self._execute_listen(channel)
        return self._conn

    def fileno(self) -> int:
        """Socket fd to register with the event loop poller."""
        return self.connection.fileno()

    def listen(self, channel: str) -> None:
        _check_channel(channel)
        if channel not in self._channels:
            self._channels.add(channel)
            self._execute_listen(channel)

    def unlisten(self, channel: str) -> None:
        _check_channel(channel)
        if channel in self._channels:
            self._channels.discard(channel)
            self.connection.execute(sql.SQL("UNLISTEN {}").format(sql.Identifier(channel)))

    def notify(self, channel: str, payload: str) -> None:
        """Publish a fanout message. Runs on the storage/publish side."""
        _check_channel(channel)
        encoded = payload.encode("utf-8")
        if len(encoded) > MAX_NOTIFY_PAYLOAD:
            raise ValueError(
                f"NOTIFY payload for channel {channel!r} is {len(encoded)} bytes, "
                f"exceeds PostgreSQL limit of {MAX_NOTIFY_PAYLOAD}"
            )
        self.connection.execute("SELECT pg_notify(%s, %s)", (channel, payload))

    def drain(self) -> Iterator[Notification]:
        """
        Non-blocking read of pending notifications.

        Call this when the fd is reported readable by the event loop. Uses the
        low-level pgconn API so it never blocks waiting for the next NOTIFY
        (``Connection.notifies()`` would block until one arrives).
        """
        conn = self.connection

        # A notification that arrives while this connection is executing a
        # query (LISTEN/UNLISTEN on subscription changes) is parsed by psycopg
        # into its high-level backlog and never reaches the low-level pgconn
        # queue below — without this, such a broadcast is silently lost.
        backlog = conn._notifies_backlog
        while backlog:
            queued = backlog.popleft()
            yield Notification(channel=queued.channel, payload=queued.payload)

        conn.pgconn.consume_input()
        while (raw := conn.pgconn.notifies()) is not None:
            yield Notification(
                channel=raw.relname.decode("utf-8"),
                payload=raw.extra.decode("utf-8"),
            )

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
        self._conn = None
        self._channels.clear()

    def _execute_listen(self, channel: str) -> None:
        # channel already validated before it reaches _channels; Identifier
        # quoting is defense in depth on top of that
        self.connection.execute(sql.SQL("LISTEN {}").format(sql.Identifier(channel)))


def _check_channel(channel: str) -> None:
    if not _SAFE_CHANNEL.match(channel):
        raise ValueError(f"Unsafe NOTIFY channel name: {channel!r}")
