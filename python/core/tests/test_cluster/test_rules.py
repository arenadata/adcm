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

from operator import itemgetter
from unittest import TestCase

from core.legacy.cluster.errors import ClusterAddHostError
from core.legacy.cluster.rules import (
    CandidateViolation,
    CandidateViolationType,
    HostCandidateDTO,
    check_hosts_can_be_added_to_cluster,
    detect_valid_host_candidates,
    find_host_candidate_violations,
)
from core.legacy.cluster.types import HostAddInfo


def with_cluster(host: HostAddInfo, cluster_id: int | None) -> HostAddInfo:
    return HostAddInfo(id=host.id, name=host.name, original_id=host.original_id, cluster_id=cluster_id)


class TestClusterHostCandidates(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.host_1 = HostAddInfo(id=1, name="host-1", original_id=None, cluster_id=None)
        self.host_1_d1 = HostAddInfo(id=10, name="host-1-duplicate-1", original_id=1, cluster_id=None)
        self.host_2 = HostAddInfo(id=2, name="host-2", original_id=None, cluster_id=None)
        self.host_2_d1 = HostAddInfo(id=20, name="host-2-duplicate-1", original_id=2, cluster_id=None)
        self.host_3 = HostAddInfo(id=3, name="host-3", original_id=None, cluster_id=None)

    def assert_candidates(self, actual: list[HostAddInfo], expected: list[HostAddInfo]) -> None:
        by_id = itemgetter(0)
        actual_pairs = sorted(((h.id, h.name) for h in actual), key=by_id)
        expected_pairs = sorted(((h.id, h.name) for h in expected), key=by_id)

        self.assertListEqual(actual_pairs, expected_pairs)

    def test_adcm_7489_too_strict_filtering(self):
        host_1_in_cluster = with_cluster(host=self.host_1, cluster_id=1)
        payload = HostCandidateDTO(
            cluster_id=1,
            in_cluster=[host_1_in_cluster],
            candidates=[self.host_1_d1, self.host_2, self.host_2_d1, self.host_3],
        )
        expected_candidates = [self.host_2, self.host_2_d1, self.host_3]

        candidates = detect_valid_host_candidates(payload=payload)

        self.assert_candidates(actual=candidates, expected=expected_candidates)

    def test_adcm_7489_check_hosts_can_be_added_to_cluster_two_duplicates_fail(self):
        payload = HostCandidateDTO(
            cluster_id=1,
            in_cluster=[],
            candidates=[self.host_1, self.host_1_d1],
        )

        with self.assertRaises(ClusterAddHostError):
            check_hosts_can_be_added_to_cluster(payload=payload)

    def test_adcm_7489_check_hosts_can_be_added_to_cluster_duplicates_to_added_duplicate_fail(self):
        host_1_duplicate_in_cluster = with_cluster(host=self.host_1_d1, cluster_id=1)
        duplicate_2 = HostAddInfo(id=11, name="host-1-duplicate-2", original_id=1, cluster_id=None)
        payload = HostCandidateDTO(
            cluster_id=1,
            in_cluster=[host_1_duplicate_in_cluster],
            candidates=[self.host_1, duplicate_2],
        )

        with self.assertRaises(ClusterAddHostError):
            check_hosts_can_be_added_to_cluster(payload=payload)

    def test_adcm_7489_check_hosts_can_be_added_to_cluster_fail(self):
        host_1_in_cluster = with_cluster(host=self.host_1, cluster_id=1)
        payload = HostCandidateDTO(
            cluster_id=1,
            in_cluster=[host_1_in_cluster],
            candidates=[self.host_1_d1],
        )

        with self.assertRaises(ClusterAddHostError):
            check_hosts_can_be_added_to_cluster(payload=payload)

    def test_bound_duplicate_to_empty_cluster_allowed(self):
        payload = HostCandidateDTO(
            cluster_id=1,
            in_cluster=[],
            candidates=[self.host_1_d1],
        )

        check_hosts_can_be_added_to_cluster(payload=payload)

    def test_duplicate_not_in_candidates_when_original_added(self):
        payload = HostCandidateDTO(
            cluster_id=1,
            in_cluster=[self.host_1],
            candidates=[self.host_1_d1, self.host_2, self.host_2_d1],
        )

        candidates = detect_valid_host_candidates(payload=payload)

        self.assert_candidates(actual=candidates, expected=[self.host_2, self.host_2_d1])

    def test_duplicate_not_in_candidates_when_another_duplicate_added(self):
        duplicate_in_cluster = with_cluster(host=self.host_1_d1, cluster_id=1)
        duplicate_2 = HostAddInfo(id=11, name="host-1-duplicate-2", original_id=1, cluster_id=None)
        payload = HostCandidateDTO(
            cluster_id=1,
            in_cluster=[duplicate_in_cluster],
            candidates=[duplicate_in_cluster, duplicate_2, self.host_1, self.host_2, self.host_2_d1],
        )

        candidates = detect_valid_host_candidates(payload=payload)

        self.assert_candidates(actual=candidates, expected=[self.host_2, self.host_2_d1])

    def test_duplicate_by_name_in_candidates_to_empty_cluster_fail(self):
        host_1 = HostAddInfo(id=1, name="host-1", cluster_id=None, original_id=None)
        host_2 = HostAddInfo(id=2, name="host-1", cluster_id=None, original_id=3)
        payload = HostCandidateDTO(
            cluster_id=1,
            in_cluster=[],
            candidates=[host_1, host_2],
        )

        with self.assertRaises(ClusterAddHostError):
            check_hosts_can_be_added_to_cluster(payload=payload)

    def test_duplicate_by_name_in_candidates_when_same_name_in_cluster_fail(self):
        host_1 = HostAddInfo(id=1, name="host-1", cluster_id=None, original_id=None)
        host_2 = HostAddInfo(id=2, name="host-1", cluster_id=None, original_id=3)
        payload = HostCandidateDTO(
            cluster_id=1,
            in_cluster=[host_1],
            candidates=[host_2],
        )

        with self.assertRaises(ClusterAddHostError):
            check_hosts_can_be_added_to_cluster(payload=payload)

    def test_detect_foreign_cluster(self):
        host_1 = HostAddInfo(id=1, name="host-1", cluster_id=1, original_id=None)
        payload = HostCandidateDTO(cluster_id=2, in_cluster=[], candidates=[host_1])

        expected_violation = CandidateViolation(
            host=host_1, level="candidates", type=CandidateViolationType.BOUND_ANOTHER
        )

        violations = find_host_candidate_violations(payload)

        self.assertListEqual(violations, [expected_violation])
