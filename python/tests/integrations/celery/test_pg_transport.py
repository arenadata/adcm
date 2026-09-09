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
Unit coverage for the PostgreSQL kombu transport.

Storage semantics run against the regular test database through a real kombu
``Connection`` (SQLAlchemy side) and a real ``ListenConnection`` (psycopg
LISTEN/NOTIFY side). What is *not* covered here — a live worker consuming via
the event loop, pidbox over fanout, cross-process delivery — lives in
``tests_integration/test_as_containers/test_pg_transport.py``.
"""

from queue import Empty
from unittest import TestCase
from unittest.mock import patch
import time

from django.db import connection as django_connection
from django.test import TestCase as DjangoTestCase
from integrations.celery.pg import transport
from integrations.celery.pg.listen import (
    MAX_NOTIFY_PAYLOAD,
    ListenConnection,
    sqlalchemy_url_to_dsn,
)
from integrations.celery.pg.models import Binding, Message, Queue
from kombu import Connection
from sqlalchemy import URL


class TestNamingAndUrls(TestCase):
    def test_broker_url_selects_this_transport(self):
        url = transport.make_broker_url("postgresql+psycopg://u:p@h:5/db")

        self.assertEqual(url, "integrations.celery.pg.transport:Transport+postgresql+psycopg://u:p@h:5/db")

    def test_channel_names_are_safe_postgres_identifiers(self):
        # exchange/queue names may contain dots and be arbitrarily long;
        # NOTIFY channels must be plain identifiers <= 63 bytes
        for name in ("celery.pidbox", "celery", "reply.a3f1-very-long-" + "x" * 200):
            for derived in (transport.fanout_channel_name(name), transport.wakeup_channel_name(name)):
                self.assertRegex(derived, r"^[A-Za-z_][A-Za-z0-9_]*$")
                self.assertLessEqual(len(derived), 63)

    def test_channel_names_are_stable_and_collision_resistant(self):
        self.assertEqual(transport.fanout_channel_name("celery.pidbox"), transport.fanout_channel_name("celery.pidbox"))
        self.assertNotEqual(transport.fanout_channel_name("celery.pidbox"), transport.fanout_channel_name("celery"))
        # same source name routed through different prefixes must not collide
        self.assertNotEqual(transport.fanout_channel_name("celery"), transport.wakeup_channel_name("celery"))

    def test_sqlalchemy_url_to_dsn_drops_driver_and_keeps_credentials(self):
        dsn = sqlalchemy_url_to_dsn("postgresql+psycopg://user:secret@host:5432/db")

        self.assertTrue(dsn.startswith("postgresql://"))
        self.assertIn("secret", dsn)
        self.assertNotIn("+psycopg", dsn)

    def test_unsafe_channel_names_are_rejected(self):
        listen_connection = ListenConnection(dsn="unused")

        for unsafe in ("kombu; DROP TABLE x", 'kombu"quoted', "1starts_with_digit", ""):
            with self.assertRaisesRegex(ValueError, "Unsafe NOTIFY channel name"):
                listen_connection.listen(unsafe)

    def test_oversized_notify_payload_fails_loudly(self):
        listen_connection = ListenConnection(dsn="unused")

        with self.assertRaisesRegex(ValueError, "exceeds PostgreSQL limit"):
            listen_connection.notify("kombu_fanout_test", "x" * (MAX_NOTIFY_PAYLOAD + 1))


class PGTransportStorageTest(DjangoTestCase):
    """Channel storage semantics on the real test database."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dsn = _sqlalchemy_test_dsn()
        cls.broker_url = transport.make_broker_url(cls.dsn)

        # the engine cache must not outlive the test database
        def _drop_engines():
            for engine, _ in transport._ENGINES.values():
                engine.dispose()
            transport._ENGINES.clear()

        cls.addClassCleanup(_drop_engines)

    def setUp(self):
        self.kombu_connection = Connection(self.broker_url)
        self.addCleanup(self.kombu_connection.close)
        self.channel = self.kombu_connection.channel()

        # sqlalchemy writes bypass django's per-test transaction; clean manually
        session = self.channel.session
        for model in (Message, Binding, Queue):
            session.query(model).delete()
        session.commit()

    def test_put_get_roundtrip_preserves_frame_in_fifo_order(self):
        self.channel._put("q1", self._frame("t1", body="first"))
        self.channel._put("q1", self._frame("t2", body="second"))

        self.assertEqual(self.channel._get("q1")["body"], "first")
        self.assertEqual(self.channel._get("q1")["body"], "second")

    def test_get_on_empty_queue_raises_empty(self):
        with self.assertRaises(Empty):
            self.channel._get("q_empty")

    def test_claimed_message_is_invisible_but_kept_until_ack(self):
        self.channel._put("q1", self._frame("t1"))

        self.channel._get("q1")

        # invisible to other consumers, but the row is kept for ack/restore
        with self.assertRaises(Empty):
            self.channel._get("q1")
        self.assertEqual(self.channel._size("q1"), 1)
        self.assertIn("t1", self.channel._claimed_rows)

    def test_ack_via_kombu_api_deletes_the_row(self):
        queue = self.kombu_connection.SimpleQueue("q_ack", channel=self.channel)
        self.addCleanup(queue.close)

        queue.put({"n": 1})
        message = queue.get_nowait()
        self.assertEqual(message.payload, {"n": 1})

        message.ack()

        self.assertEqual(self.channel._size("q_ack"), 0)
        self.assertEqual(self.channel._claimed_rows, {})

    def test_poison_payload_is_dropped_not_claimed_forever(self):
        session = self.channel.session
        queue_row = self.channel._get_or_create_queue("q_poison")
        session.add(Message("{not json", queue_row))
        session.commit()

        with self.assertRaises(Empty):
            self.channel._get("q_poison")

        # the undecodable row is deleted, not left invisible in the table
        self.assertEqual(self.channel._size("q_poison"), 0)

    def test_purge_empties_queue_and_reports_count(self):
        self.channel._put("q1", self._frame("t1"))
        self.channel._put("q1", self._frame("t2"))

        self.assertEqual(self.channel._purge("q1"), 2)
        self.assertEqual(self.channel._size("q1"), 0)

    def test_delete_removes_queue_messages_and_bindings(self):
        self.channel._put("q_del", self._frame("t1"))
        self.channel._queue_bind(exchange="ex", routing_key="rk", pattern="", queue="q_del")

        self.channel._delete("q_del")

        session = self.channel.session
        self.assertEqual(session.query(Queue).filter(Queue.name == "q_del").count(), 0)
        self.assertEqual(session.query(Binding).filter(Binding.queue == "q_del").count(), 0)

    def test_bindings_are_persisted_for_other_processes_and_deduplicated(self):
        self.channel._queue_bind(exchange="ex", routing_key="rk", pattern="", queue="q_bound")
        self.channel._queue_bind(exchange="ex", routing_key="rk", pattern="", queue="q_bound")

        # a channel with no in-memory state (≈ another process) sees the binding
        other_channel = self.kombu_connection.channel()
        self.assertEqual(other_channel.get_table("ex"), [["rk", "", "q_bound"]])

    def test_queue_declare_is_idempotent(self):
        first = self.channel._get_or_create_queue("q_decl")
        second = self.channel._get_or_create_queue("q_decl")

        self.assertEqual(first.id, second.id)

    def test_queue_declare_survives_a_lost_insert_race(self):
        # two workers booting at once both declare `celery`: patching the lookup
        # to miss reproduces the window where the other process committed the row
        # after our SELECT but before our INSERT
        existing = self.channel._get_or_create_queue("q_race")

        with patch("sqlalchemy.orm.Query.first", return_value=None):
            recovered = self.channel._get_or_create_queue("q_race")

        self.assertEqual(recovered.id, existing.id)
        self.assertEqual(self.channel.session.query(Queue).filter(Queue.name == "q_race").count(), 1)

    def test_ensure_tables_is_idempotent(self):
        engine, _ = transport._ENGINES[self.dsn]

        transport._ensure_tables(engine)
        transport._ensure_tables(engine)

    @staticmethod
    def _frame(tag: str, body: str = "payload") -> dict:
        # minimal kombu message frame: delivery_tag is what ack/restore key on
        return {"body": body, "properties": {"delivery_tag": tag}}


class ListenConnectionTest(DjangoTestCase):
    """LISTEN/NOTIFY roundtrip on the dedicated psycopg connection."""

    def setUp(self):
        self.listen_connection = ListenConnection(dsn=sqlalchemy_url_to_dsn(_sqlalchemy_test_dsn()))
        self.addCleanup(self.listen_connection.close)

    def test_notify_reaches_listener_and_drain_is_non_blocking(self):
        # notify on the listening connection itself makes the notification
        # arrive during query processing — the psycopg-backlog path that
        # drain() must cover, or broadcasts landing during LISTEN/UNLISTEN
        # execution are silently lost
        self.listen_connection.listen("kombu_unit_chan")

        self.listen_connection.notify("kombu_unit_chan", '{"method": "ping"}')

        self.assertEqual(self._drain_with_deadline(), [("kombu_unit_chan", '{"method": "ping"}')])
        # nothing pending -> drain returns immediately with no items
        self.assertEqual(list(self.listen_connection.drain()), [])

    def test_unlisten_stops_delivery(self):
        self.listen_connection.listen("kombu_unit_chan")
        self.listen_connection.unlisten("kombu_unit_chan")

        self.listen_connection.notify("kombu_unit_chan", "lost")

        self.assertEqual(self._drain_with_deadline(timeout=0.5), [])

    def _drain_with_deadline(self, timeout: float = 5.0) -> list:
        # NOTIFY delivery is asynchronous; poll the non-blocking drain
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            notifications = list(self.listen_connection.drain())
            if notifications:
                return notifications
            time.sleep(0.02)
        return []


def _sqlalchemy_test_dsn() -> str:
    settings = django_connection.settings_dict
    return URL.create(
        "postgresql+psycopg",
        username=settings["USER"],
        password=settings["PASSWORD"],
        host=settings["HOST"],
        port=int(settings["PORT"]),
        database=settings["NAME"],
    ).render_as_string(hide_password=False)
