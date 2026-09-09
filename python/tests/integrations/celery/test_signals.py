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
Unit coverage for the prefork fork-safety handlers.

These tests exercise the handlers through the real celery signals, but without
forking: what actually fires the signals in a live worker is celery itself —
``worker_process_init`` in every pool child regardless of pool type, and
``worker_before_create_process`` before every fork of the async (AsynPool)
pool, which ADCM uses because the PG transport declares
``implements.asynchronous=True``. End-to-end fork behavior (initial pool,
replacement children, parent/child socket isolation) is integration territory.
"""

from unittest import TestCase
from unittest.mock import Mock, patch

from integrations.celery import signals
from integrations.celery.pg import transport

from celery.signals import worker_before_create_process, worker_process_init

_DSN = "postgresql+psycopg://inherited-from-parent"


class TestForkSafetyHandlers(TestCase):
    def setUp(self):
        signals.install_for_worker()

        self._engines_before = dict(transport._ENGINES)
        transport._ENGINES.clear()

    def tearDown(self):
        transport._ENGINES.clear()
        transport._ENGINES.update(self._engines_before)

    def test_child_discards_inherited_engines_without_closing_parent_sockets(self):
        engine = Mock()
        transport._ENGINES[_DSN] = (engine, Mock())

        with patch.object(signals.connections, "close_all") as close_all:
            worker_process_init.send(sender=None)

        close_all.assert_called_once()
        # close=True would send Terminate over sockets the parent still uses
        engine.dispose.assert_called_once_with(close=False)
        self.assertEqual(transport._ENGINES, {})

    def test_parent_keeps_engines_before_fork(self):
        engine = Mock()
        transport._ENGINES[_DSN] = (engine, Mock())

        with patch.object(signals.connections, "close_all") as close_all:
            worker_before_create_process.send(sender=None)

        # django connections are closed so the child inherits no socket...
        close_all.assert_called_once()
        engine.dispose.assert_not_called()
        self.assertIn(_DSN, transport._ENGINES)

    def test_repeated_install_does_not_duplicate_receivers(self):
        signals.install_for_worker()
        signals.install_for_worker()

        with (
            patch.object(signals.connections, "close_all") as close_all,
            patch.object(signals, "discard_engines_inherited_from_fork") as discard,
        ):
            worker_process_init.send(sender=None)

        close_all.assert_called_once()
        discard.assert_called_once()

    def test_child_rebuilds_engine_lazily_after_discard(self):
        transport._ENGINES[_DSN] = (Mock(), Mock())

        transport.discard_engines_inherited_from_fork()

        channel = Mock(spec=["connection"])
        channel.connection.client.hostname = _DSN
        with (
            patch.object(transport, "create_engine") as create_engine,
            patch.object(transport, "_ensure_tables") as ensure_tables,
        ):
            engine, session_factory = transport.Channel._open(channel)

        create_engine.assert_called_once_with(_DSN)
        ensure_tables.assert_called_once_with(create_engine.return_value)
        self.assertIs(engine, create_engine.return_value)
        self.assertIsNotNone(session_factory)
