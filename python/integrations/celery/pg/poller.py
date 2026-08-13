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
Async poller for the fanout (``LISTEN``) side of the transport.

Analogous to redis' ``MultiChannelPoller``: it tracks channels that have active
fanout subscriptions, exposes their ``LISTEN`` socket file descriptors so the
kombu event loop can ``select`` on them, and on readability drains pending
notifications and delivers them to the owning channel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from integrations.celery.pg.transport import Channel


class FanoutPoller:
    """Maps ``LISTEN`` socket fds to the channels waiting on them."""

    def __init__(self) -> None:
        self._channels: set[Channel] = set()

    def add(self, channel: Channel) -> None:
        self._channels.add(channel)

    def discard(self, channel: Channel) -> None:
        self._channels.discard(channel)

    def close(self) -> None:
        self._channels.clear()

    @property
    def fds(self) -> dict[int, Channel]:
        """Current fd -> channel map for channels with live subscriptions."""
        mapping: dict[int, Channel] = {}
        for channel in self._channels:
            if channel.active_fanout_queues or channel.active_wakeup_queues:
                mapping[channel.listen_connection.fileno()] = channel
        return mapping

    def on_readable(self, fileno: int) -> None:
        """Called by the event loop when a ``LISTEN`` socket has data."""
        channel = self.fds.get(fileno)
        if channel is not None:
            channel.handle_notifications()
