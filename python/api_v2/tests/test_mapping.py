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

from api_v2.cluster.utils import get_requires
from api_v2.tests.base import BaseAPITestCase
from cm.models import HostComponent, ServiceComponent
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED


class TestMapping(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_1")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)

        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_2")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )
        self.component_2 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_2"
        )

        self.add_hostcomponent_map(
            cluster=self.cluster_1,
            hc_map=[{"host_id": self.host_1.pk, "service_id": self.service_1.pk, "component_id": self.component_1.pk}],
        )

    def test_list_mapping_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertDictEqual(response.json()[0], {"componentId": 1, "hostId": 1, "id": 1})

    def test_create_mapping_success(self):
        host_3 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_3")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host_3)
        component_2 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_2"
        )
        data = [
            {"hostId": host_3.pk, "componentId": component_2.pk},
            {"hostId": self.host_1.pk, "componentId": self.component_1.pk},
        ]

        response = self.client.post(
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.cluster_1.pk}), data=data
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 2)

    def test_create_empty_mapping_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.cluster_1.pk}),
            data=[],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 0)

    def test_mapping_hosts_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-mapping-hosts", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual({host["id"] for host in response.json()}, {self.host_1.pk, self.host_2.pk})

    def test_mapping_components_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-mapping-components", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual({component["id"] for component in response.json()}, {self.component_1.pk, self.component_2.pk})

    def test_mapping_components_with_requires_success(self):
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_requires_component")
        cluster = self.add_cluster(bundle=bundle, name="cluster_requires")
        self.add_services_to_cluster(service_names=["hbase", "zookeeper", "hdfs"], cluster=cluster)

        response = self.client.get(path=reverse(viewname="v2:cluster-mapping-components", kwargs={"pk": cluster.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 3)

        for component_data in data:
            component = ServiceComponent.objects.filter(prototype__name=component_data["name"], cluster=cluster).first()

            if not component.prototype.requires:
                self.assertIsNone(component_data["dependOn"])
                continue

            self.assertEqual(len(component.prototype.requires), len(component_data["dependOn"]))

    def test_mapping_components_with_cyclic_dependencies_success(self):
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_cyclic_dependencies")
        cluster = self.add_cluster(bundle=bundle, name="cluster_cyclic_dependencies")
        self.add_services_to_cluster(
            service_names=["serviceA", "serviceB", "serviceC", "serviceD", "serviceE"], cluster=cluster
        )

        response = self.client.get(path=reverse(viewname="v2:cluster-mapping-components", kwargs={"pk": cluster.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 5)

        for component_data in data:
            component = ServiceComponent.objects.filter(prototype__name=component_data["name"], cluster=cluster).first()
            requires = component.prototype.requires[0]
            expected_service_name = component_data["dependOn"][0]["servicePrototype"]["name"]
            expected_component_name = component_data["dependOn"][0]["servicePrototype"]["componentPrototypes"][0][
                "name"
            ]
            self.assertEqual(requires["service"], expected_service_name)
            self.assertEqual(requires["component"], expected_component_name)

    def test_get_requires(self):
        requires = [{"service": "service1", "component": "component1"}, {"service": "service1"}]

        new_requires = get_requires(requires=requires)

        self.assertDictEqual(new_requires, {"service1": ["component1"]})
