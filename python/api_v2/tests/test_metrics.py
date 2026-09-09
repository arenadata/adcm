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

from cm.models import Cluster, Host, HostInfo, Service
from core.status import FullStatusMap
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from tests.dependencies import get_status_scenarios_manager
from tests.suites import ADCMDjangoAPISuite

CLUSTER_METRICS_PATH = "cluster-metrics"


class TestClusterMetrics(ADCMDjangoAPISuite):
    maxDiff = None

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
        cls.host_7 = cls.uc.add_host(provider=cls.provider, fqdn="metrics-host-7", cluster=cls.cluster_2)

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

        cls.fresh_cluster = cls.uc.add_cluster(bundle=cls.bundle_1, name="fresh_cluster")

        _create_hosts_info(
            hosts=[cls.host_1, cls.host_2, cls.host_3, cls.host_4, cls.host_5, cls.host_6],
            metrics=cls.metrics,
        )

    def test_cluster_metrics_list_success(self):
        # prepare objects and its statuses
        self.uc.add_services_to_cluster(
            names=["service_1", "service_2", "service_3_manual_add"], cluster=self.cluster_1
        )
        service_1_id, service_2_id, service_3_id = (
            Service.objects.filter(cluster=self.cluster_1).order_by("id").values_list("id", flat=True)
        )

        status_map = FullStatusMap.model_validate(
            {
                "clusters": {
                    str(self.cluster_1.pk): {
                        "status": 0,
                        "hosts": {},  # metrics does not care about this field
                        "services": {  # all up
                            str(id_): {"status": 0, "components": {}, "details": []}
                            for id_ in (service_1_id, service_2_id, service_3_id)
                        },
                    },
                    # DO NOT UNCOMMENT/DELETE. case: object exists, status is not
                    # str(cls.cluster_2.pk): {},
                    str(self.fresh_cluster.pk): {
                        "status": 16,
                        "hosts": {},
                        "services": {},
                    },
                },
                "hosts": {
                    **{
                        str(host.id): {"status": 2}
                        for host in (self.host_1, self.host_2, self.host_3, self.host_4, self.host_5, self.host_6)
                    },
                    str(self.host_7.id): {"status": 0},
                },
            }
        )
        get_status_scenarios_manager().set_status_map(status_map)

        # set mapping, put host_1 to MM = indirect service in MM
        service = Service.objects.get(prototype__name="service_1", cluster=self.cluster_1)
        self.uc.set_hostcomponent(
            cluster=self.cluster_1, entries=((self.host_1, component) for component in service.components.all())
        )
        response = self.client.v2[self.host_1, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = (self.client.v2 / CLUSTER_METRICS_PATH).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 3)
        self.assertCountEqual(
            data["results"],
            [
                {
                    "id": self.cluster_1.id,
                    "resources": {
                        # sum of cpu_vcores of host_1, host_2, host_3
                        "cpuVcores": 12,
                        # sum of ram of host_1, host_2, host_3 in gib
                        "ram": {"value": 6.0, "unit": "GiB"},
                        # sum of disk_size of host_1, host_2, host_3 in pib
                        "disk": {"value": 999.13, "unit": "PiB"},
                    },
                    "services": {
                        "count": 3,
                        "up": 3,
                        "down": 0,
                        "maintenanceMode": 1,  # indirect
                    },
                    "hosts": {"count": 3, "up": 0, "down": 3, "maintenanceMode": 1},
                },
                {
                    "id": self.cluster_2.id,
                    "resources": {
                        "cpuVcores": 8,
                        "ram": {"value": 0.85, "unit": "GiB"},
                        "disk": {"value": 40.0, "unit": "TiB"},
                    },
                    "services": {"count": 0, "up": 0, "down": 0, "maintenanceMode": 0},
                    # one host is a duplicate, both down in status_map
                    "hosts": {"count": 3, "up": 1, "down": 2, "maintenanceMode": 0},
                },
                {  # case: no HostInfo data
                    "id": self.fresh_cluster.id,
                    "resources": None,
                    "services": {"count": 0, "up": 0, "down": 0, "maintenanceMode": 0},
                    "hosts": {"count": 0, "up": 0, "down": 0, "maintenanceMode": 0},
                },
            ],
        )

    def test_cluster_metrics_list_limit_offset_success(self):
        response = (self.client.v2 / CLUSTER_METRICS_PATH).get(query={"limit": 1, "offset": 1})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_cluster_metrics_retrieve_success(self):
        # prepare objects and its statuses
        self.uc.add_services_to_cluster(
            names=["service_1", "service_2", "service_3_manual_add"], cluster=self.cluster_1
        )
        service_1_id, service_2_id, service_3_id = (
            Service.objects.filter(cluster=self.cluster_1).order_by("id").values_list("id", flat=True)
        )
        service_with_passive_monitoring = self.uc.add_services_to_cluster(
            names=["service_6_delete_with_action"], cluster=self.cluster_1
        )[0]
        prototype = service_with_passive_monitoring.prototype
        prototype.monitoring = "passive"
        prototype.save(update_fields=["monitoring"])

        status_map = FullStatusMap.model_validate(
            {
                "clusters": {
                    str(self.cluster_1.pk): {
                        "status": 0,
                        "services": {
                            str(service_1_id): {"status": 0, "components": {}, "details": []},
                            # missing status considered DOWN
                            # str(service_2_id): {"status": 0, "components": {}, "details": []},
                            str(service_3_id): {"status": 4, "components": {}, "details": []},
                            # passive monitoring considered UP
                            str(service_with_passive_monitoring.id): {"status": 8, "components": {}, "details": []},
                        },
                        "hosts": {},  # metrics does not care about this field
                    },
                },
                "hosts": {
                    str(self.host_1.id): {"status": 0},
                    str(self.host_2.id): {"status": 8},
                    str(self.host_3.id): {"status": 16},
                },
            }
        )
        get_status_scenarios_manager().set_status_map(status_map)

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
                "services": {"count": 4, "up": 2, "down": 2, "maintenanceMode": 0},
                "hosts": {"count": 3, "up": 1, "down": 2, "maintenanceMode": 0},
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
                # no status data here, all missing statuses considered DOWN
                "services": {"count": 0, "up": 0, "down": 0, "maintenanceMode": 0},
                "hosts": {"count": 3, "up": 0, "down": 3, "maintenanceMode": 0},
            },
        )

    def test_cluster_metrics_retrieve_not_found_fail(self):
        non_exist_cluster = self.get_non_existent_pk(model=Cluster)
        response = (self.client.v2 / CLUSTER_METRICS_PATH / non_exist_cluster).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_adcm_8267_retrieve_no_resources_no_status_data_success(self):
        response = (self.client.v2 / CLUSTER_METRICS_PATH / self.fresh_cluster.id).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "id": self.fresh_cluster.id,
                "resources": None,
                # no status data here
                "services": {"count": 0, "up": 0, "down": 0, "maintenanceMode": 0},
                "hosts": {"count": 0, "up": 0, "down": 0, "maintenanceMode": 0},
            },
        )


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
