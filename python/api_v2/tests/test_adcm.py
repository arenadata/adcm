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

from cm.models import ADCM, Action
from django.conf import settings
from rest_framework.status import HTTP_200_OK

from api_v2.tests.base import BaseAPITestCase


class TestADCM(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def test_retrieve_success(self):
        response = self.client.v2["adcm"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], ADCM.objects.first().pk)

    def test_list_actions_success(self):
        response = self.client.v2["adcm", "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_retrieve_actions_success(self):
        response = self.client.v2["adcm", "actions", Action.objects.last().pk].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], Action.objects.last().pk)

    def test_get_versions_success(self):
        response = self.client.versions.get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(response.json(), {"adcm": {"version": settings.ADCM_VERSION}})

    def test_adcm_5461_adcm_basic_actions_success(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.v2["adcm", "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)
