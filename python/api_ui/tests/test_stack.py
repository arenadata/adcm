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

from cm.models import Bundle, ObjectType, Prototype
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.tests.base import BaseTestCase


class TestStackClusterPrototypeUIAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()

        self.test_prototype_1 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.CLUSTER,
            version="1",
            name="test_prototype",
            display_name="test_prototype",
        )
        self.test_prototype_2 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.CLUSTER,
            version="2",
            name="test_prototype",
            display_name="test_prototype",
        )
        self.test_prototype_3 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.CLUSTER,
            version="1",
            name="test_prototype_2",
            display_name="test_prototype_2",
        )
        self.test_prototype_4 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.CLUSTER,
            version="3",
            name="test_prototype_2",
            display_name="test_prototype_2",
        )

    def test_get_cluster_prototypes_success(self):
        response: Response = self.client.get(path=reverse("api_ui:cluster-list"))
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertEqual(len(response_json["results"][0]["versions"]), 2)
        self.assertEqual(len(response_json["results"][1]["versions"]), 2)

    def test_ordering_id_success(self):
        response: Response = self.client.get(path=reverse("api_ui:cluster-list"), data={"ordering": "id"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_1.display_name, self.test_prototype_3.display_name],
        )

    def test_ordering_id_reverse_success(self):
        response: Response = self.client.get(path=reverse("api_ui:cluster-list"), data={"ordering": "-id"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_3.display_name, self.test_prototype_1.display_name],
        )

    def test_ordering_name_success(self):
        response: Response = self.client.get(path=reverse("api_ui:cluster-list"), data={"ordering": "name"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_1.display_name, self.test_prototype_3.display_name],
        )

    def test_ordering_name_reverse_success(self):
        response: Response = self.client.get(path=reverse("api_ui:cluster-list"), data={"ordering": "-name"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_3.display_name, self.test_prototype_1.display_name],
        )

    def test_ordering_display_name_success(self):
        response: Response = self.client.get(path=reverse("api_ui:cluster-list"), data={"ordering": "display_name"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_1.display_name, self.test_prototype_3.display_name],
        )

    def test_ordering_display_name_reverse_success(self):
        response: Response = self.client.get(path=reverse("api_ui:cluster-list"), data={"ordering": "-display_name"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_3.display_name, self.test_prototype_1.display_name],
        )


class TestStackProviderPrototypeUIAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()

        self.test_prototype_1 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.PROVIDER,
            version="1",
            name="test_prototype",
            display_name="test_prototype",
        )
        self.test_prototype_2 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.PROVIDER,
            version="2",
            name="test_prototype",
            display_name="test_prototype",
        )
        self.test_prototype_3 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.PROVIDER,
            version="1",
            name="test_prototype_2",
            display_name="test_prototype_2",
        )

    def test_get_cluster_prototypes_success(self):
        response: Response = self.client.get(path=reverse("api_ui:provider-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNotNone(response.data)

    def test_ordering_id_success(self):
        response: Response = self.client.get(path=reverse("api_ui:provider-list"), data={"ordering": "id"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_1.display_name, self.test_prototype_3.display_name],
        )

    def test_ordering_id_reverse_success(self):
        response: Response = self.client.get(path=reverse("api_ui:provider-list"), data={"ordering": "-id"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_3.display_name, self.test_prototype_1.display_name],
        )

    def test_ordering_name_success(self):
        response: Response = self.client.get(path=reverse("api_ui:provider-list"), data={"ordering": "name"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_1.display_name, self.test_prototype_3.display_name],
        )

    def test_ordering_name_reverse_success(self):
        response: Response = self.client.get(path=reverse("api_ui:provider-list"), data={"ordering": "-name"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_3.display_name, self.test_prototype_1.display_name],
        )

    def test_ordering_display_name_success(self):
        response: Response = self.client.get(path=reverse("api_ui:provider-list"), data={"ordering": "display_name"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_1.display_name, self.test_prototype_3.display_name],
        )

    def test_ordering_display_name_reverse_success(self):
        response: Response = self.client.get(path=reverse("api_ui:provider-list"), data={"ordering": "-display_name"})
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response_json["count"], 2)
        self.assertListEqual(
            [test_prototype["display_name"] for test_prototype in response_json["results"]],
            [self.test_prototype_3.display_name, self.test_prototype_1.display_name],
        )
