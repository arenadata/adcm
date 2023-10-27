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

from api_v2.tests.base import BaseAPITestCase
from cm.models import ADCM, Action
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK


class TestADCM(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

    def test_retrieve_success(self):
        response = self.client.get(path=reverse(viewname="v2:adcm-detail"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], ADCM.objects.first().pk)

    def test_list_actions_success(self):
        response = self.client.get(path=reverse(viewname="v2:adcm-action-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_retrieve_actions_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:adcm-action-detail", kwargs={"pk": Action.objects.last().pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], Action.objects.last().pk)