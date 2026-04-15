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

from cm.legacy.services.status.client import FullStatusMap
from cm.models import ADCMEntityStatus, SignatureStatus
from tests.dependencies import get_status_scenarios_manager
from tests.suites import ADCMFiltersDataSuite


class TestFilters(ADCMFiltersDataSuite):
    def setUp(self) -> None:
        super().setUp()

        self.clusters_url = self.client.v2 / "clusters"
        self.bundles_url = self.client.v2 / "bundles"

        self.set_cluster_state(self.cl_1, "installed")
        self.set_bundle_signature_status(self.bundle_cl_1, SignatureStatus.VALID)

    def test_ordering_bundles(self) -> None:
        cases = [
            ("displayName", "displayName", ["A Cluster", "A Cluster", "B Cluster"]),
            (
                "uploadTime",
                "uploadTime",
                [
                    self.normalize_upload_time(value)
                    for value in (self.bundle_cl_1.date, self.bundle_cl_2.date, self.bundle_cl_3.date)
                ],
            ),
            ("version", "version", ["1.0.1", "12.0.0", "2.0.0"]),
            ("edition", "edition", ["community", "community", "enterprise"]),
            (
                "mainPrototypeLicenseStatus",
                "mainPrototype.license.status",
                ["absent", "absent", "accepted"],
            ),
            ("signatureStatus", "signatureStatus", ["absent", "absent", "valid"]),
        ]

        for ordering_field, value_path, asc_expected_value in cases:
            with self.subTest(direction="asc", ordering_field=ordering_field):
                results = self.get_results(self.bundles_url, value_path, query={"ordering": ordering_field})
                self.assertEqual(asc_expected_value, results)

            with self.subTest(direction="desc", ordering_field=ordering_field):
                results = self.get_results(self.bundles_url, value_path, query={"ordering": f"-{ordering_field}"})
                self.assertEqual(list(reversed(asc_expected_value)), results)

    def test_filters_bundles(self) -> None:
        cases = [
            ("id", "id", self.bundle_cl_1.pk, [self.bundle_cl_1.pk], "0"),
            ("displayName", "displayName", "A CLU", ["A Cluster", "A Cluster"], "wrong"),  # check icontains
            ("edition", "edition", "enterprise", ["enterprise"], "ent"),  # check exact
            ("version", "version", "1.0.1", ["1.0.1"], "1"),  # check exact
            ("mainPrototypeLicenseStatus", "mainPrototype.license.status", "accepted", ["accepted"], "unaccepted"),
            (
                "product",
                "mainPrototype.name",
                "B_CLUSTER",
                [
                    "b_cluster",
                ],
                "b_clus",
            ),  # check iexact
            (
                "uploadTime",
                "uploadTime",
                self.normalize_upload_time(self.bundle_cl_1.date),
                [self.normalize_upload_time(self.bundle_cl_1.date)],
                "2020-04-09T12:48:02.075849Z",
            ),
            ("signatureStatus", "signatureStatus", "valid", ["valid"], "invalid"),
        ]

        for filter_field, value_path, matched_query_value, matched_expected_value, empty_query_value in cases:
            with self.subTest(filter_result="matched", filter_field=filter_field):
                results = self.get_results(self.bundles_url, value_path, query={filter_field: matched_query_value})
                self.assertEqual(matched_expected_value, results)

            with self.subTest(filter_result="empty", filter_field=filter_field):
                results = self.get_results(self.bundles_url, value_path, query={filter_field: empty_query_value})
                self.assertEqual([], results)

    def test_ordering_clusters(self) -> None:
        cases = [
            ("name", "name", ["cluster_1", "cluster_2", "cluster_3"]),
            ("prototypeName", "prototype.name", ["a_cluster", "a_cluster", "b_cluster"]),
            (
                "prototypeDisplayName",
                "prototype.displayName",
                ["A Cluster", "A Cluster", "B Cluster"],
            ),
            ("prototypeVersion", "prototype.version", ["1.0.1", "12.0.0", "2.0.0"]),
            ("state", "state", ["created", "created", "installed"]),
        ]

        for ordering_field, value_path, asc_expected_value in cases:
            with self.subTest(direction="asc", ordering_field=ordering_field):
                results = self.get_results(self.clusters_url, value_path, query={"ordering": ordering_field})
                self.assertEqual(asc_expected_value, results)

            with self.subTest(direction="desc", ordering_field=ordering_field):
                results = self.get_results(self.clusters_url, value_path, query={"ordering": f"-{ordering_field}"})
                expected_values = list(reversed(asc_expected_value))
                self.assertEqual(expected_values, results)

    def test_filters_clusters(self) -> None:
        cases = [
            ("id", "id", self.cl_1.pk, [self.cl_1.pk], "0"),
            ("name", "name", "ER_1", ["cluster_1"], "wrong"),  #  check icontains
            ("prototypeName", "prototype.name", "a_cluster", ["a_cluster", "a_cluster"], "wrong"),
            (
                "prototypeDisplayName",
                "prototype.displayName",
                "A Cluster",
                ["A Cluster", "A Cluster"],
                "wrong",
            ),
            ("state", "state", "installed", ["installed"], "wrong"),
            ("prototypeVersion", "prototype.version", "1.0.1", ["1.0.1"], "1"),
        ]

        for filter_field, value_path, matched_query_value, matched_expected_value, empty_query_value in cases:
            with self.subTest(filter_result="matched", filter_field=filter_field):
                results = self.get_results(self.clusters_url, value_path, query={filter_field: matched_query_value})
                self.assertEqual(matched_expected_value, results)

            with self.subTest(filter_result="empty", filter_field=filter_field):
                results = self.get_results(self.clusters_url, value_path, query={filter_field: empty_query_value})
                self.assertEqual([], results)

    def test_status_filters(self) -> None:
        status_map = FullStatusMap.model_validate(
            {
                "clusters": {
                    str(self.cl_1.pk): {"services": {}, "status": 0, "hosts": {}},
                }
            }
        )

        manager = get_status_scenarios_manager()
        manager.set_status_map(status_map)
        response = self.get_r(url=self.clusters_url, query={"status": "up"})

        result = self.extract_values(response["results"], "status")
        expected_value = [ADCMEntityStatus.UP.value]
        self.assertEqual(expected_value, result)
