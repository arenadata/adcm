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

from typing import Final

from cm.impl.object.repo import ObjectRepo
from cm.tests.utils import gen_cluster
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.test import TransactionTestCase, tag
from tests.integrations.concurrency.parallel import SyncedCall, run_concurrently
from tests.integrations.concurrency.test_examples import BaseScenarioTestCase
from tests.integrations.concurrency.utils import BRANCH_START
from tests.integrations.constants import INTEGRATION_TESTS_TAG

LOCK_SYNC: Final = "cm.impl.locks.repo.LockRepo.register_lock_on_object_waiting"
MULTI_STATE_UPDATE_SYNC: Final = "tests.integrations.concurrency.test_multi_state.apply_multi_state_update"


def apply_multi_state_update(
    owner: CoreObjectDescriptor, add: tuple[str, ...] = (), remove: tuple[str, ...] = ()
) -> None:
    ObjectRepo().update_multi_state(object_=owner, add=add, remove=remove)


@tag(INTEGRATION_TESTS_TAG)
class TestMultiStateConcurrency(BaseScenarioTestCase):
    def assert_cluster_multi_state(self, *states: str) -> None:
        self.cluster.refresh_from_db()
        self.assertCountEqual(self.cluster.multi_state, states)

    def assert_synchronized(self, outcomes) -> None:
        """No errors, every branch read the object before any sibling wrote"""

        self.assertEqual(
            [(outcome.error, outcome.synchronized) for outcome in outcomes],
            [(None, True)] * len(outcomes),
        )

    def test_multi_state_set_twice_keeps_both_flags(self) -> None:
        set_first_multi_state, set_second_multi_state = self.prepare_script_group("multi_state_set_twice")

        outcomes = run_concurrently(
            SyncedCall(func=set_first_multi_state, sync_before=LOCK_SYNC),
            SyncedCall(func=set_second_multi_state, sync_before=LOCK_SYNC),
        )

        self.assert_synchronized(outcomes)
        self.assert_cluster_multi_state("first", "second")

    def test_multi_state_set_and_state_keeps_both(self) -> None:
        set_multi_state, set_state = self.prepare_script_group("multi_state_set_and_state")

        outcomes = run_concurrently(
            SyncedCall(func=set_multi_state, sync_before=LOCK_SYNC),
            SyncedCall(func=set_state, sync_before=LOCK_SYNC),
        )

        self.assert_synchronized(outcomes)
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.state, "changed")
        self.assertCountEqual(self.cluster.multi_state, ["first"])

    def test_before_upgrade_clean_does_not_clobber_state_and_multi_state(self) -> None:
        self.cluster.before_upgrade = {"state": "created", "bundle_id": self.cluster.prototype.bundle_id}
        self.cluster.save(update_fields=["before_upgrade"])

        clean_before_upgrade, set_multi_state, set_state = self.prepare_script_group(
            "before_upgrade_clean_with_state_and_multi_state"
        )

        outcomes = run_concurrently(
            SyncedCall(func=clean_before_upgrade, sync_before=BRANCH_START),
            SyncedCall(func=set_multi_state, sync_before=LOCK_SYNC),
            SyncedCall(func=set_state, sync_before=LOCK_SYNC),
        )

        self.assert_synchronized(outcomes)
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.state, "changed")
        self.assertCountEqual(self.cluster.multi_state, ["first"])
        self.assertDictEqual(self.cluster.before_upgrade, {"state": None})

    def test_multi_state_set_twice_sequentially_keeps_both_flags(self) -> None:
        set_first_multi_state, set_second_multi_state = self.prepare_script_group("multi_state_set_twice")

        set_first_multi_state()
        set_second_multi_state()

        self.assert_cluster_multi_state("first", "second")


@tag(INTEGRATION_TESTS_TAG)
class TestObjectRepoMultiStateConcurrency(TransactionTestCase):
    def setUp(self) -> None:
        self.cluster = gen_cluster()

    def test_update_multi_state_concurrently_adds_both_flags(self) -> None:
        owner = CoreObjectDescriptor(id=self.cluster.id, type=ADCMCoreType.CLUSTER)

        outcomes = run_concurrently(
            SyncedCall(
                func=lambda: apply_multi_state_update(owner=owner, add=("first",)),
                sync_before=MULTI_STATE_UPDATE_SYNC,
            ),
            SyncedCall(
                func=lambda: apply_multi_state_update(owner=owner, add=("second",)),
                sync_before=MULTI_STATE_UPDATE_SYNC,
            ),
        )

        self.assertEqual(
            [(outcome.error, outcome.synchronized) for outcome in outcomes],
            [(None, True)] * len(outcomes),
        )
        self.cluster.refresh_from_db()
        self.assertCountEqual(self.cluster.multi_state, ["first", "second"])

    def test_update_multi_state_concurrently_adds_and_removes(self) -> None:
        owner = CoreObjectDescriptor(id=self.cluster.id, type=ADCMCoreType.CLUSTER)
        self.cluster.set_multi_state("second")

        outcomes = run_concurrently(
            SyncedCall(
                func=lambda: apply_multi_state_update(owner=owner, add=("first",)),
                sync_before=MULTI_STATE_UPDATE_SYNC,
            ),
            SyncedCall(
                func=lambda: apply_multi_state_update(owner=owner, remove=("second",)),
                sync_before=MULTI_STATE_UPDATE_SYNC,
            ),
        )

        self.assertEqual(
            [(outcome.error, outcome.synchronized) for outcome in outcomes],
            [(None, True)] * len(outcomes),
        )
        self.cluster.refresh_from_db()
        self.assertCountEqual(self.cluster.multi_state, ["first"])
