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

from collections.abc import Callable
from dataclasses import dataclass
import time
import threading

from cm.impl.locks.repo import LockRepo, pg_advisory_xact_lock
from core.types import ADCMCoreType, ClusterDesc, Descriptor
from django.db import IntegrityError, connection, connections, transaction
from django.test import SimpleTestCase

COUNTER_TABLE = "test_advisory_lock_counter"
UNIQUE_TABLE = "test_advisory_lock_unique"

WORKERS_AMOUNT = 4
# arbitrary key pair, it only has to be shared by workers
RACE_LOCK_NAMESPACE = 44100
RACE_LOCK_KEY = 1

# --- parallel run helper: start ---

# guard against hanging only, never reached when workers behave
RUN_TIMEOUT = 60
# how often sync point re-checks workers blocked on the advisory lock
POLL_INTERVAL = 0.005


class SyncPoint:
    """
    Point between reading data and writing it, which workers pass only together.

    Worker waits until every other worker either reached this point (or finished),
    or is blocked waiting for advisory lock on `namespace`/`key`.
    Without the lock it works as barrier: all reads happen before any write.
    With the lock, holder proceeds as soon as siblings are seen waiting for it in `pg_locks`,
    so serialization is proven by Postgres rather than by waiting for some time.
    """

    def __init__(self, parties: int, namespace: int, key: int) -> None:
        self._parties = parties
        self._namespace = namespace
        self._key = key
        self._arrived: set[threading.Thread] = set()
        self._condition = threading.Condition()

    def wait(self) -> None:
        self.mark_arrived()

        while True:
            # queried outside of condition, so siblings aren't held while Postgres answers
            lock_waiters = self.count_lock_waiters()

            with self._condition:
                if len(self._arrived) + lock_waiters >= self._parties:
                    return

                self._condition.wait(timeout=POLL_INTERVAL)

    def mark_arrived(self) -> None:
        """Count current thread as arrived, repeated calls from the same thread change nothing"""

        with self._condition:
            # thread objects rather than idents: ident of finished thread may be reused
            self._arrived.add(threading.current_thread())
            self._condition.notify_all()

    def count_lock_waiters(self) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_locks "
                "WHERE locktype = 'advisory' AND NOT granted AND classid = %s AND objid = %s AND objsubid = 2",
                [self._namespace, self._key],
            )
            (amount,) = cursor.fetchone()

        return amount


Worker = Callable[[SyncPoint], None]


@dataclass(slots=True)
class WorkerOutcome:
    error: BaseException | None = None


def run_in_parallel(worker: Worker, amount: int) -> tuple[WorkerOutcome, ...]:
    """
    Run `worker` in `amount` threads, each in its own connection inside one non-nested transaction.

    Worker should wait at the given sync point between reading data and writing it,
    so that without serialization all reads happen before any write.
    Errors are captured per worker, not raised.
    """

    sync = SyncPoint(parties=amount, namespace=RACE_LOCK_NAMESPACE, key=RACE_LOCK_KEY)
    outcomes = tuple(WorkerOutcome() for _ in range(amount))

    def run(outcome: WorkerOutcome) -> None:
        try:
            with transaction.atomic():
                worker(sync)
        except BaseException as e:  # noqa: BLE001
            outcome.error = e
        finally:
            # siblings shouldn't wait for worker that won't reach the sync point anymore
            sync.mark_arrived()
            # connections are per thread, so only the ones opened by this worker are closed
            connections.close_all()

    threads = tuple(
        threading.Thread(target=run, args=(outcome,), name=f"lock-worker-{i}", daemon=True)
        for i, outcome in enumerate(outcomes)
    )

    deadline = time.monotonic() + RUN_TIMEOUT
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=max(deadline - time.monotonic(), 0))

    if hanging := [thread.name for thread in threads if thread.is_alive()]:
        message = f"Workers aren't finished in {RUN_TIMEOUT}s: {', '.join(hanging)}"
        raise TimeoutError(message)

    return outcomes


# --- parallel run helper: end ---


def increment_counter(sync: SyncPoint) -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT value FROM {COUNTER_TABLE} WHERE id = 1")  # noqa: S608
        (value,) = cursor.fetchone()

        sync.wait()

        cursor.execute(f"UPDATE {COUNTER_TABLE} SET value = %s WHERE id = 1", [value + 1])  # noqa: S608


def insert_next_id(sync: SyncPoint) -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {UNIQUE_TABLE}")  # noqa: S608
        (max_id,) = cursor.fetchone()

        sync.wait()

        cursor.execute(f"INSERT INTO {UNIQUE_TABLE} (id) VALUES (%s)", [max_id + 1])  # noqa: S608


def increment_counter_locked(sync: SyncPoint) -> None:
    pg_advisory_xact_lock(namespace=RACE_LOCK_NAMESPACE, key=RACE_LOCK_KEY)
    increment_counter(sync)


def insert_next_id_locked(sync: SyncPoint) -> None:
    pg_advisory_xact_lock(namespace=RACE_LOCK_NAMESPACE, key=RACE_LOCK_KEY)
    insert_next_id(sync)


class TestAdvisoryLockRace(SimpleTestCase):
    # workers need data committed to see it from their connections, so no per-test transactions
    databases = {"default"}

    def setUp(self) -> None:
        super().setUp()

        with connection.cursor() as cursor:
            cursor.execute(f"CREATE TABLE {COUNTER_TABLE} (id integer PRIMARY KEY, value integer NOT NULL)")
            cursor.execute(f"INSERT INTO {COUNTER_TABLE} (id, value) VALUES (1, 0)")  # noqa: S608
            cursor.execute(f"CREATE TABLE {UNIQUE_TABLE} (id integer PRIMARY KEY)")

        self.addCleanup(self.drop_tables)

    def drop_tables(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {COUNTER_TABLE}, {UNIQUE_TABLE}")

    def read_counter(self) -> int:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT value FROM {COUNTER_TABLE} WHERE id = 1")  # noqa: S608
            (value,) = cursor.fetchone()

        return value

    def read_ids(self) -> list[int]:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT id FROM {UNIQUE_TABLE} ORDER BY id")  # noqa: S608
            return [id_ for (id_,) in cursor.fetchall()]

    def test_counter_without_lock_loses_updates(self) -> None:
        outcomes = run_in_parallel(increment_counter, amount=WORKERS_AMOUNT)

        self.assertEqual([outcome.error for outcome in outcomes], [None] * WORKERS_AMOUNT)
        self.assertLess(self.read_counter(), WORKERS_AMOUNT)

    def test_counter_with_lock_equals_sequential(self) -> None:
        outcomes = run_in_parallel(increment_counter_locked, amount=WORKERS_AMOUNT)

        self.assertEqual([outcome.error for outcome in outcomes], [None] * WORKERS_AMOUNT)
        self.assertEqual(self.read_counter(), WORKERS_AMOUNT)

    def test_unique_insert_without_lock_conflicts(self) -> None:
        outcomes = run_in_parallel(insert_next_id, amount=WORKERS_AMOUNT)

        errors = [outcome.error for outcome in outcomes if outcome.error is not None]
        self.assertTrue(errors)
        for error in errors:
            self.assertIsInstance(error, IntegrityError)
        self.assertLess(len(self.read_ids()), WORKERS_AMOUNT)

    def test_unique_insert_with_lock_equals_sequential(self) -> None:
        outcomes = run_in_parallel(insert_next_id_locked, amount=WORKERS_AMOUNT)

        self.assertEqual([outcome.error for outcome in outcomes], [None] * WORKERS_AMOUNT)
        self.assertListEqual(self.read_ids(), list(range(1, WORKERS_AMOUNT + 1)))


class TestLockRepo(SimpleTestCase):
    # lock is bound to transaction, so it has to be real and non-nested
    databases = {"default"}

    def setUp(self) -> None:
        super().setUp()

        self.repo = LockRepo()
        self.cluster: ClusterDesc = Descriptor(id=12, type=ADCMCoreType.CLUSTER)

    def read_own_advisory_locks(self) -> list[tuple[str, int, int, int]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT locktype, classid::bigint, objid::bigint, objsubid FROM pg_locks "
                "WHERE pid = pg_backend_pid() AND locktype = 'advisory'"
            )
            return [tuple(row) for row in cursor.fetchall()]

    def test_lock_on_cluster_uses_cluster_namespace_and_id(self) -> None:
        with transaction.atomic():
            self.repo.register_lock_on_object_waiting(target=self.cluster)

            locks = self.read_own_advisory_locks()

        self.assertListEqual(locks, [("advisory", 44100, self.cluster.id, 2)])

    def test_lock_is_reentrant_within_transaction(self) -> None:
        with transaction.atomic():
            self.repo.register_lock_on_object_waiting(target=self.cluster)
            self.repo.register_lock_on_object_waiting(target=self.cluster)

            locks = self.read_own_advisory_locks()

        self.assertListEqual(locks, [("advisory", 44100, self.cluster.id, 2)])

    def test_lock_outside_transaction_fails(self) -> None:
        with self.assertRaises(RuntimeError):
            self.repo.register_lock_on_object_waiting(target=self.cluster)
