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
            display_name="test_prototype",
        )
        self.test_prototype_2 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.CLUSTER,
            version="2",
            display_name="test_prototype",
        )
        self.test_prototype_3 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.CLUSTER,
            version="1",
            display_name="test_prototype_2",
        )

    def test_get_cluster_prototypes_success(self):
        response: Response = self.client.get(path=reverse("api_ui:cluster-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNotNone(response.data)


class TestStackProviderPrototypeUIAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()

        self.test_prototype_1 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.PROVIDER,
            version="1",
            display_name="test_prototype",
        )
        self.test_prototype_2 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.PROVIDER,
            version="2",
            display_name="test_prototype",
        )
        self.test_prototype_3 = Prototype.objects.create(
            bundle=bundle,
            type=ObjectType.PROVIDER,
            version="1",
            display_name="test_prototype_2",
        )

    def test_get_cluster_prototypes_success(self):
        response: Response = self.client.get(path=reverse("api_ui:provider-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNotNone(response.data)
