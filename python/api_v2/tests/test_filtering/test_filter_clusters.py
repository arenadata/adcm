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
from cm.models import ADCMEntityStatus
from tests.dependencies import get_status_scenarios_manager
from tests.suites import ADCMFiltersDataSuite


class TestFilters(ADCMFiltersDataSuite):
    def setUp(self) -> None:
        super().setUp()

        self.clusters_url = self.client.v2 / "clusters"
        self.set_cluster_state(self.cl_1, "installed")

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

        self.set_cluster_state(self.cl_1, "installed")

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
            ("name__contains", "name", "1", ["cluster_1"], "wrong"),
            ("name__icontains", "name", "CLUSTER_1", ["cluster_1"], "wrong"),
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

        self.set_cluster_state(self.cl_1, "installed")

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
