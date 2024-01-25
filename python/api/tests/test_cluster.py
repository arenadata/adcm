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

from adcm.tests.base import BaseTestCase
from cm.models import (
    Action,
    ActionType,
    Bundle,
    Cluster,
    ObjectType,
    Prototype,
    Upgrade,
)
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK


class TestClusterAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create(name="test_cluster_prototype")
        self.cluster_prototype = Prototype.objects.create(
            bundle=self.bundle,
            version=2,
            name="test_cluster_prototype",
        )
        self.cluster = Cluster.objects.create(prototype=self.cluster_prototype)

        new_bundle = Bundle.objects.create(name="bundle")
        self.service_prototype_1_1 = Prototype.objects.create(
            bundle=new_bundle,
            type=ObjectType.SERVICE,
            shared=True,
            name="service_prototype_1",
            display_name="service_prototype_1",
            version=2,
        )
        self.service_prototype_2_2 = Prototype.objects.create(
            bundle=new_bundle,
            type=ObjectType.SERVICE,
            shared=True,
            name="service_prototype_2",
            display_name="service_prototype_2",
            version=1,
        )

    def test_upgrade(self):
        Upgrade.objects.create(
            bundle=self.bundle,
            min_version=1,
            max_version=3,
            action=Action.objects.create(
                prototype=self.cluster_prototype,
                type=ActionType.JOB,
                state_available="any",
            ),
        )
        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-upgrade", kwargs={"cluster_id": self.cluster.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_ordering_id_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-service-prototype", kwargs={"cluster_id": self.cluster.pk}),
            data={"ordering": "id"},
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response_json), 2)
        self.assertListEqual(
            [test_prototype["id"] for test_prototype in response_json],
            sorted((self.service_prototype_1_1.pk, self.service_prototype_2_2.pk)),
        )

    def test_ordering_id_reverse_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-service-prototype", kwargs={"cluster_id": self.cluster.pk}),
            data={"ordering": "-id"},
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response_json), 2)
        self.assertListEqual(
            [test_prototype["id"] for test_prototype in response_json],
            sorted((self.service_prototype_1_1.pk, self.service_prototype_2_2.pk), reverse=True),
        )

    def test_ordering_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-service-prototype", kwargs={"cluster_id": self.cluster.pk}),
            data={"ordering": "name"},
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response_json), 2)
        self.assertListEqual(
            [test_prototype["name"] for test_prototype in response_json],
            sorted((self.service_prototype_1_1.name, self.service_prototype_2_2.name)),
        )

    def test_ordering_name_reverse_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-service-prototype", kwargs={"cluster_id": self.cluster.pk}),
            data={"ordering": "-name"},
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response_json), 2)
        self.assertListEqual(
            [test_prototype["name"] for test_prototype in response_json],
            sorted((self.service_prototype_1_1.name, self.service_prototype_2_2.name), reverse=True),
        )

    def test_ordering_display_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-service-prototype", kwargs={"cluster_id": self.cluster.pk}),
            data={"ordering": "display_name"},
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response_json), 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json],
            sorted((self.service_prototype_1_1.display_name, self.service_prototype_2_2.display_name)),
        )

    def test_ordering_display_name_reverse_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-service-prototype", kwargs={"cluster_id": self.cluster.pk}),
            data={"ordering": "-display_name"},
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response_json), 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json],
            sorted((self.service_prototype_1_1.display_name, self.service_prototype_2_2.display_name), reverse=True),
        )

    def test_ordering_version_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-service-prototype", kwargs={"cluster_id": self.cluster.pk}),
            data={"ordering": "version"},
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response_json), 2)
        self.assertListEqual(
            [int(test_prototype["version"]) for test_prototype in response_json],
            sorted((self.service_prototype_1_1.version, self.service_prototype_2_2.version)),
        )

    def test_ordering_version_reverse_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:cluster-service-prototype", kwargs={"cluster_id": self.cluster.pk}),
            data={"ordering": "-version"},
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response_json), 2)
        self.assertListEqual(
            [int(test_prototype["version"]) for test_prototype in response_json],
            sorted((self.service_prototype_1_1.version, self.service_prototype_2_2.version), reverse=True),
        )
