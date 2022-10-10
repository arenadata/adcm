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

from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.tests.base import BaseTestCase
from cm.models import ADCM
from init_db import init as init_adcm


class TestADCM(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        init_adcm()

    def test_list(self):
        adcm = ADCM.objects.select_related("prototype").last()
        test_data = {
            "id": adcm.id,
            "name": adcm.name,
            "prototype_id": adcm.prototype.id,
            "state": adcm.state,
            "url": f"http://testserver/api/v1/adcm/{adcm.id}/",
        }

        response: Response = self.client.get(reverse("adcm-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertDictEqual(response.json()["results"][0], test_data)

    def test_list_interface(self):
        adcm = ADCM.objects.select_related("prototype").last()
        test_data = {
            "id": adcm.id,
            "name": adcm.name,
            "prototype_id": adcm.prototype.id,
            "state": adcm.state,
            "url": f"http://testserver/api/v1/adcm/{adcm.id}/",
            "prototype_version": adcm.prototype.version,
            "bundle_id": adcm.prototype.bundle_id,
            "config": f"http://testserver/api/v1/adcm/{adcm.id}/config/",
            "action": f"http://testserver/api/v1/adcm/{adcm.id}/action/",
            "multi_state": [],
            "concerns": [],
            "locked": adcm.locked,
            "main_info": None,
        }

        response: Response = self.client.get(f"{reverse('adcm-list')}?view=interface")

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertDictEqual(response.json()["results"][0], test_data)

    def test_retrieve(self):
        adcm = ADCM.objects.select_related("prototype").last()
        test_data = {
            "id": adcm.id,
            "name": adcm.name,
            "prototype_id": adcm.prototype.id,
            "state": adcm.state,
            "url": f"http://testserver/api/v1/adcm/{adcm.id}/",
            "prototype_version": adcm.prototype.version,
            "bundle_id": adcm.prototype.bundle_id,
            "config": f"http://testserver/api/v1/adcm/{adcm.id}/config/",
            "action": f"http://testserver/api/v1/adcm/{adcm.id}/action/",
            "multi_state": [],
            "concerns": [],
            "locked": adcm.locked,
        }

        response: Response = self.client.get(reverse("adcm-detail", kwargs={"adcm_pk": adcm.id}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(response.json(), test_data)

    def test_retrieve_interface(self):
        adcm = ADCM.objects.select_related("prototype").last()
        test_data = {
            "id": adcm.id,
            "name": adcm.name,
            "prototype_id": adcm.prototype.id,
            "state": "created",
            "url": f"http://testserver/api/v1/adcm/{adcm.id}/",
            "prototype_version": adcm.prototype.version,
            "bundle_id": adcm.prototype.bundle_id,
            "config": f"http://testserver/api/v1/adcm/{adcm.id}/config/",
            "action": f"http://testserver/api/v1/adcm/{adcm.id}/action/",
            "multi_state": [],
            "concerns": [],
            "locked": adcm.locked,
            "main_info": None,
        }

        response: Response = self.client.get(
            f"{reverse('adcm-detail', kwargs={'adcm_pk': adcm.id})}?view=interface"
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(response.json(), test_data)
