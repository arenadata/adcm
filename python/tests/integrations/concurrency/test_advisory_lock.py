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
from functools import partial

from cm.impl.locks.repo import LockRepo, pg_advisory_xact_lock
from core.types import ADCMCoreType, ClusterDesc, Descriptor
from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase, tag
from tests.integrations.concurrency.parallel import SyncedCall, run_concurrently
from tests.integrations.constants import INTEGRATION_TESTS_TAG

COUNTER_TABLE = "test_advisory_lock_counter"
UNIQUE_TABLE = "test_advisory_lock_unique"

WORKERS_AMOUNT = 4
# arbitrary key pair, it only has to be shared by workers
RACE_LOCK_NAMESPACE = 413000
RACE_LOCK_KEY = 1

SYNC_POINT = f"{__name__}.sync_point"


def sync_point(): ...


def increment_counter() -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT value FROM {COUNTER_TABLE} WHERE id = 1")  # noqa: S608
        (value,) = cursor.fetchone()

        sync_point()

        cursor.execute(f"UPDATE {COUNTER_TABLE} SET value = %s WHERE id = 1", [value + 1])  # noqa: S608


def insert_next_id() -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {UNIQUE_TABLE}")  # noqa: S608
        (max_id,) = cursor.fetchone()

        sync_point()

        cursor.execute(f"INSERT INTO {UNIQUE_TABLE} (id) VALUES (%s)", [max_id + 1])  # noqa: S608


def increment_counter_locked() -> None:
    pg_advisory_xact_lock(namespace=RACE_LOCK_NAMESPACE, key=RACE_LOCK_KEY)
    increment_counter()


def insert_next_id_locked() -> None:
    pg_advisory_xact_lock(namespace=RACE_LOCK_NAMESPACE, key=RACE_LOCK_KEY)
    insert_next_id()


def run_in_parallel(f: Callable, amount: int = WORKERS_AMOUNT):
    return run_concurrently(*(SyncedCall(func=transaction.atomic(f), sync_before=SYNC_POINT) for _ in range(amount)))


def change_with_cluster_lock(cluster_id: int, data: dict, repo: LockRepo, *, key: int | str | None = None):
    # GIL will sequentially execute lines in each thread, but lock on same object will make further code waiting
    with transaction.atomic():
        repo.register_lock_on_object_waiting(Descriptor(id=cluster_id, type=ADCMCoreType.CLUSTER))
        read_value = data["value"]
        sync_point()
        # in case require lock on same cluster_id, but each thread write to its own key
        change_key = key or cluster_id
        write_value = f"{read_value}-{change_key}"
        data[f"cluster-{change_key}"] = {"read": read_value, "write": write_value}
        data["value"] = write_value


@tag(INTEGRATION_TESTS_TAG)
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
        outcomes = run_in_parallel(increment_counter)

        self.assertEqual([outcome.error for outcome in outcomes], [None] * WORKERS_AMOUNT)
        self.assertLess(self.read_counter(), WORKERS_AMOUNT)

    def test_counter_with_lock_equals_sequential(self) -> None:
        outcomes = run_in_parallel(increment_counter_locked)

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


@tag(INTEGRATION_TESTS_TAG)
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

        self.assertListEqual(locks, [("advisory", 413000, self.cluster.id, 2)])

    def test_lock_is_reentrant_within_transaction(self) -> None:
        with transaction.atomic():
            self.repo.register_lock_on_object_waiting(target=self.cluster)
            self.repo.register_lock_on_object_waiting(target=self.cluster)

            locks = self.read_own_advisory_locks()

        self.assertListEqual(locks, [("advisory", 413000, self.cluster.id, 2)])

    def test_lock_outside_transaction_fails(self) -> None:
        with self.assertRaises(RuntimeError):
            self.repo.register_lock_on_object_waiting(target=self.cluster)

    def test_lock_same_object(self):
        data: dict = {"value": "initial"}
        change_data = partial(change_with_cluster_lock, data=data, repo=self.repo)

        outcomes = run_concurrently(
            SyncedCall(func=partial(change_data, cluster_id=10, key=10), sync_before=SYNC_POINT),
            SyncedCall(func=partial(change_data, cluster_id=10, key=20), sync_before=SYNC_POINT),
        )

        # all synced by lock, not sync point
        self.assertSetEqual({(o.synchronized, o.serialized_by_lock) for o in outcomes}, {(False, True)})

        # due to race there are two possible conditions of who got there first
        match data["value"]:
            case "initial-10-20":
                self.assertDictEqual(data["cluster-10"], {"read": "initial", "write": "initial-10"})
                self.assertDictEqual(data["cluster-20"], {"read": "initial-10", "write": "initial-10-20"})
            case "initial-20-10":
                self.assertDictEqual(data["cluster-10"], {"read": "initial-20", "write": "initial-20-10"})
                self.assertDictEqual(data["cluster-20"], {"read": "initial", "write": "initial-20"})
            case another:
                raise AssertionError(f"Unexpected outcome: {another}")

    def test_lock_different_objects(self):
        data: dict = {"value": "initial"}
        change_data = partial(change_with_cluster_lock, data=data, repo=self.repo)

        outcomes = run_concurrently(
            SyncedCall(func=partial(change_data, cluster_id=10), sync_before=SYNC_POINT),
            SyncedCall(func=partial(change_data, cluster_id=20), sync_before=SYNC_POINT),
        )

        # effectivealy locks on two different object just "don't work"
        self.assertSetEqual({(o.synchronized, o.serialized_by_lock) for o in outcomes}, {(True, False)})

        self.assertIn(data["value"], ("initial-10", "initial-20"))
        self.assertDictEqual(data["cluster-10"], {"read": "initial", "write": "initial-10"})
        self.assertDictEqual(data["cluster-20"], {"read": "initial", "write": "initial-20"})
