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
import time

from cm.impl.locks.repo import pg_advisory_xact_lock
from django.contrib.auth.models import Group
from django.db import connections, transaction
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test import TransactionTestCase, tag
from tests.integrations.concurrency.parallel import SyncedCall, run_concurrently
from tests.integrations.constants import INTEGRATION_TESTS_TAG
from unittest_parametrize import ParametrizedTestCase, param, parametrize

WRITE_NAME_SYNC_POINT = f"{__name__}.write_name"
RENAME_SYNC_POINT = f"{__name__}.rename"
INITIAL_NAME = "initial"
INITIAL_COUNT = 0

# arbitrary, keys only have to be shared by calls
ADVISORY_LOCK_NAMESPACE = 1
FIRST_LOCK_KEY = 1
SECOND_LOCK_KEY = 2

# long enough to tell release by locks from release by timeout
LONG_SYNC_TIMEOUT = 30


def write_name(group_id: int, name: str) -> None:
    Group.objects.filter(id=group_id).update(name=name)


def rename(group_id: int, name: str) -> None:
    Group.objects.filter(id=group_id).update(name=name)


def append_to_name(group_id: int, suffix: str) -> str:
    seen = Group.objects.get(id=group_id).name
    write_name(group_id=group_id, name=f"{seen}-{suffix}")

    return seen


def append_to_name_by_rename(group_id: int, suffix: str) -> str:
    seen = Group.objects.get(id=group_id).name
    rename(group_id=group_id, name=f"{seen}-{suffix}")

    return seen


@transaction.atomic
def append_to_name_with_row_lock(group_id: int, suffix: str) -> str:
    seen = Group.objects.select_for_update().get(id=group_id).name
    write_name(group_id=group_id, name=f"{seen}-{suffix}")

    return seen


@transaction.atomic
def append_to_name_with_advisory_locks(group_id: int, suffix: str, keys: tuple[int, ...]) -> str:
    for key in keys:
        pg_advisory_xact_lock(namespace=ADVISORY_LOCK_NAMESPACE, key=key)

    return append_to_name(group_id=group_id, suffix=suffix)


def increment_count(group_id: int) -> int:
    seen = int(Group.objects.get(id=group_id).name)
    write_name(group_id=group_id, name=str(seen + 1))

    return seen


@transaction.atomic
def increment_count_with_advisory_lock(group_id: int, key: int) -> int:
    pg_advisory_xact_lock(namespace=ADVISORY_LOCK_NAMESPACE, key=key)

    return increment_count(group_id=group_id)


@tag(INTEGRATION_TESTS_TAG)
class TestRunConcurrently(ParametrizedTestCase, TransactionTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.group = Group.objects.create(name=INITIAL_NAME)

    def test_reads_happen_before_siblings_write_success(self) -> None:
        outcomes = run_concurrently(
            SyncedCall(
                func=partial(append_to_name, group_id=self.group.id, suffix="a"), sync_before=WRITE_NAME_SYNC_POINT
            ),
            SyncedCall(
                func=partial(append_to_name, group_id=self.group.id, suffix="b"), sync_before=WRITE_NAME_SYNC_POINT
            ),
        )

        self.assertEqual(
            [(o.result, o.error, o.synchronized, o.serialized_by_lock) for o in outcomes],
            [(INITIAL_NAME, None, True, False)] * 2,
        )

        # one update is lost: that's the race being reproduced
        self.group.refresh_from_db()
        self.assertIn(self.group.name, {f"{INITIAL_NAME}-a", f"{INITIAL_NAME}-b"})

    @parametrize("threads", [param(5, id="5_threads"), param(10, id="10_threads")])
    def test_increments_are_lost_without_serialization_success(self, threads: int) -> None:
        self.group.name = str(INITIAL_COUNT)
        self.group.save(update_fields=["name"])

        outcomes = run_concurrently(
            *(
                SyncedCall(func=partial(increment_count, group_id=self.group.id), sync_before=WRITE_NAME_SYNC_POINT)
                for _ in range(threads)
            )
        )

        # every call read the same value before any sibling wrote
        self.assertEqual(
            [(o.result, o.error, o.synchronized, o.serialized_by_lock) for o in outcomes],
            [(INITIAL_COUNT, None, True, False)] * threads,
        )

        # N increments collapse into one: the read-modify-write race
        self.group.refresh_from_db()
        self.assertEqual(int(self.group.name), INITIAL_COUNT + 1)

    @parametrize("threads", [param(5, id="5_threads"), param(10, id="10_threads")])
    def test_increments_are_partially_lost_with_mixed_serialization_success(self, threads: int) -> None:
        self.group.name = str(INITIAL_COUNT)
        self.group.save(update_fields=["name"])

        # some calls are serialized by a shared advisory lock, the rest read without it,
        # so the final value is between a single increment and a full serialization
        locked = threads // 2
        calls = [
            SyncedCall(
                func=partial(increment_count_with_advisory_lock, group_id=self.group.id, key=FIRST_LOCK_KEY),
                sync_before=WRITE_NAME_SYNC_POINT,
            )
            for _ in range(locked)
        ]
        calls += [
            SyncedCall(func=partial(increment_count, group_id=self.group.id), sync_before=WRITE_NAME_SYNC_POINT)
            for _ in range(threads - locked)
        ]

        outcomes = run_concurrently(*calls)

        self.assertFalse(any(o.error for o in outcomes))

        self.group.refresh_from_db()
        value = int(self.group.name)
        self.assertGreaterEqual(value, INITIAL_COUNT + 1)
        self.assertLessEqual(value, INITIAL_COUNT + threads)

    def test_reads_happen_before_siblings_write_with_different_sync_points_success(self) -> None:
        outcomes = run_concurrently(
            SyncedCall(
                func=partial(append_to_name, group_id=self.group.id, suffix="a"), sync_before=WRITE_NAME_SYNC_POINT
            ),
            SyncedCall(
                func=partial(append_to_name_by_rename, group_id=self.group.id, suffix="b"),
                sync_before=RENAME_SYNC_POINT,
            ),
        )

        self.assertEqual([(o.result, o.error, o.synchronized) for o in outcomes], [(INITIAL_NAME, None, True)] * 2)

        self.group.refresh_from_db()
        self.assertIn(self.group.name, {f"{INITIAL_NAME}-a", f"{INITIAL_NAME}-b"})

    def test_sibling_sync_point_is_passed_through_success(self) -> None:
        # the second call writes through sync point of the first one and never reaches its own,
        # so it doesn't wait for the first call and doesn't hold it when it's finished
        outcomes = run_concurrently(
            SyncedCall(
                func=partial(append_to_name, group_id=self.group.id, suffix="a"), sync_before=WRITE_NAME_SYNC_POINT
            ),
            SyncedCall(func=partial(append_to_name, group_id=self.group.id, suffix="b"), sync_before=RENAME_SYNC_POINT),
        )

        self.assertEqual([(o.error, o.synchronized) for o in outcomes], [(None, False)] * 2)

    @parametrize(
        "append",
        [
            param(append_to_name_with_row_lock, id="row_lock"),
            param(partial(append_to_name_with_advisory_locks, keys=(FIRST_LOCK_KEY,)), id="advisory_lock"),
        ],
    )
    def test_calls_serialized_by_lock_are_released_without_timeout_success(self, append: Callable[..., str]) -> None:
        start = time.monotonic()
        outcomes = run_concurrently(
            *(
                SyncedCall(
                    func=partial(append, group_id=self.group.id, suffix=suffix), sync_before=WRITE_NAME_SYNC_POINT
                )
                for suffix in ("a", "b")
            ),
            sync_timeout=LONG_SYNC_TIMEOUT,
        )

        # the lock holder waits at the rendezvous only until Postgres shows the sibling blocked by it
        self.assertLess(time.monotonic() - start, LONG_SYNC_TIMEOUT)
        self.assertEqual([(o.error, o.synchronized, o.serialized_by_lock) for o in outcomes], [(None, False, True)] * 2)

        # the second call has seen the result of the first one, so nothing is lost
        seen_first, seen_second = sorted(outcome.result for outcome in outcomes)
        self.assertEqual(seen_first, INITIAL_NAME)
        self.assertIn(seen_second, {f"{INITIAL_NAME}-a", f"{INITIAL_NAME}-b"})
        self.group.refresh_from_db()
        self.assertIn(self.group.name, {f"{INITIAL_NAME}-a-b", f"{INITIAL_NAME}-b-a"})
        self.assertTrue(self.group.name.startswith(seen_second))

    def test_calls_blocked_through_each_other_are_released_without_timeout_success(self) -> None:
        # Whatever order locks are taken in, calls that can't reach the rendezvous wait for locks
        # held by the waiting ones, directly or through each other, e.g.:
        # "a" waits at the rendezvous holding the first key, "b" holds the second one and waits for the first,
        # "c" waits for the second key held by "b".
        # The first and the last calls don't share a lock, so their updates may be lost, it isn't checked.
        start = time.monotonic()
        outcomes = run_concurrently(
            *(
                SyncedCall(
                    func=partial(append_to_name_with_advisory_locks, group_id=self.group.id, suffix=suffix, keys=keys),
                    sync_before=WRITE_NAME_SYNC_POINT,
                )
                for suffix, keys in (
                    ("a", (FIRST_LOCK_KEY,)),
                    ("b", (SECOND_LOCK_KEY, FIRST_LOCK_KEY)),
                    ("c", (SECOND_LOCK_KEY,)),
                )
            ),
            sync_timeout=LONG_SYNC_TIMEOUT,
        )

        self.assertLess(time.monotonic() - start, LONG_SYNC_TIMEOUT)
        self.assertEqual([(o.error, o.synchronized) for o in outcomes], [(None, False)] * 3)
        self.assertTrue(any(o.serialized_by_lock for o in outcomes))

    def test_error_is_returned_and_siblings_are_not_held_success(self) -> None:
        error = RuntimeError("Failed before write")

        def fail() -> None:
            raise error

        start = time.monotonic()
        failed, succeeded = run_concurrently(
            SyncedCall(func=fail, sync_before=WRITE_NAME_SYNC_POINT),
            SyncedCall(
                func=partial(append_to_name, group_id=self.group.id, suffix="a"), sync_before=WRITE_NAME_SYNC_POINT
            ),
            sync_timeout=LONG_SYNC_TIMEOUT,
        )

        self.assertLess(time.monotonic() - start, LONG_SYNC_TIMEOUT)
        self.assertIs(failed.error, error)
        self.assertIsNone(failed.result)
        self.assertEqual(
            (succeeded.result, succeeded.error, succeeded.synchronized, succeeded.serialized_by_lock),
            (INITIAL_NAME, None, False, False),
        )

    def test_threads_connections_are_closed_success(self) -> None:
        def use_connection() -> BaseDatabaseWrapper:
            append_to_name(group_id=self.group.id, suffix="a")
            return connections["default"]

        outcomes = run_concurrently(*[SyncedCall(func=use_connection, sync_before=WRITE_NAME_SYNC_POINT)] * 2)

        used = [outcome.result for outcome in outcomes]
        self.assertNotIn(connections["default"], used)
        self.assertIsNot(*used)
        self.assertEqual([wrapper.connection for wrapper in used], [None, None])

    def test_less_than_two_calls_fail(self) -> None:
        with self.assertRaisesMessage(ValueError, "At least 2 calls are required"):
            run_concurrently(SyncedCall(func=lambda: None, sync_before=WRITE_NAME_SYNC_POINT))
