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

from cm.models import Cluster, Host, HostInfo
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from tests.suites import ADCMDjangoAPISuite

CLUSTER_METRICS_PATH = "cluster-metrics"


class TestClusterMetrics(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        # hosts for cluster 1
        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="metrics-host-1", cluster=cls.cluster_1)
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="metrics-host-2", cluster=cls.cluster_1)
        cls.host_3 = cls.uc.add_host(provider=cls.provider, fqdn="metrics-host-3", cluster=cls.cluster_1)
        # hosts for cluster 2
        cls.host_4 = cls.uc.add_host(provider=cls.provider, fqdn="metrics-host-4", cluster=cls.cluster_2)
        # a host without a cluster for check that its info isn't added in the result
        cls.host_5 = cls.uc.add_host(provider=cls.provider, fqdn="metrics-host-5")
        # a duplicate host for check that its info isn't added in the result
        cls.host_6 = cls.uc.add_host(provider=cls.provider, fqdn="metrics-host-6", cluster=cls.cluster_2)
        cls.host_6.original = cls.host_4
        cls.host_6.save(update_fields=["original"])

        cls.metrics = {
            cls.host_1.id: {"cpu_vcores": 2, "ram": 1024, "ram_bytes": 1024**3, "disk_size": 10 * 1024**3},
            cls.host_2.id: {"cpu_vcores": 4, "ram": 2048, "ram_bytes": 2048 * 1024**2, "disk_size": 129 * 1024**4},
            cls.host_3.id: {"cpu_vcores": 6, "ram": 3072, "ram_bytes": 3072 * 1024**2, "disk_size": 999 * 1024**5},
            cls.host_4.id: {
                "cpu_vcores": 8,
                "ram": 868,
                "ram_bytes": 868 * 1024**2,
                "disk_size": 40 * 1024**4 + 999,
            },
            cls.host_5.id: {"cpu_vcores": 2, "ram": 2048, "ram_bytes": 2048 * 1024**2, "disk_size": 2 * 1024**3},
            cls.host_6.id: {"cpu_vcores": 32, "ram": 1024, "ram_bytes": 1024**3, "disk_size": 10 * 1024**3},
        }

        _create_hosts_info(
            hosts=[cls.host_1, cls.host_2, cls.host_3, cls.host_4, cls.host_5, cls.host_6],
            metrics=cls.metrics,
        )

    def test_cluster_metrics_list_success(self):
        response = (self.client.v2 / CLUSTER_METRICS_PATH).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(
            {entry["id"]: entry["resources"] for entry in data["results"]},
            {
                self.cluster_1.id: {
                    # sum of cpu_vcores of host_1, host_2, host_3
                    "cpuVcores": 12,
                    # sum of ram of host_1, host_2, host_3 in gib
                    "ram": {"value": 6.0, "unit": "GiB"},
                    # sum of disk_size of host_1, host_2, host_3 in pib
                    "disk": {"value": 999.13, "unit": "PiB"},
                },
                self.cluster_2.id: {
                    "cpuVcores": 8,
                    "ram": {"value": 0.85, "unit": "GiB"},
                    "disk": {"value": 40.0, "unit": "TiB"},
                },
            },
        )

    def test_cluster_metrics_list_limit_offset_success(self):
        response = (self.client.v2 / CLUSTER_METRICS_PATH).get(query={"limit": 1, "offset": 1})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_cluster_metrics_retrieve_success(self):
        response = (self.client.v2 / CLUSTER_METRICS_PATH / self.cluster_1.id).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "id": self.cluster_1.id,
                "resources": {
                    "cpuVcores": 12,
                    "ram": {"value": 6.0, "unit": "GiB"},
                    "disk": {"value": 999.13, "unit": "PiB"},
                },
            },
        )

    def test_cluster_metrics_retrieve_without_new_fact_fields(self):
        # delete fields "ram_bytes", "disk_size"
        HostInfo.objects.filter(host=self.host_4).update(
            value={
                "cpu_vcores": 2,
                "ram": 1024,
                "os": {"distribution": "Ubuntu"},
                "devices": [],
            },
        )

        response = (self.client.v2 / CLUSTER_METRICS_PATH / self.cluster_2.id).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "id": self.cluster_2.id,
                "resources": {
                    "cpuVcores": 2,
                    "ram": {"value": 0, "unit": "GiB"},
                    "disk": {"value": 0, "unit": "GiB"},
                },
            },
        )

    def test_cluster_metrics_retrieve_not_found_fail(self):
        non_exist_cluster = self.get_non_existent_pk(model=Cluster)
        response = (self.client.v2 / CLUSTER_METRICS_PATH / non_exist_cluster).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)


def _get_host_facts(metrics: dict) -> dict:
    return {
        **metrics,
        "os": {"distribution": "Ubuntu"},
        "devices": [],
    }


def _create_hosts_info(hosts: list[Host], metrics: dict) -> None:
    HostInfo.objects.bulk_create(
        HostInfo(host=host, value=_get_host_facts(metrics[host.pk]), hash="") for host in hosts
    )
