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
from cm.converters import orm_object_to_core_type
from cm.issue import add_concern_to_object
from cm.models import ADCM, ConcernCause
from cm.services.concern import create_issue
from core.types import CoreObjectDescriptor
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK


class TestADCM(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.adcm = ADCM.objects.select_related("prototype").last()
        self.concern = create_issue(
            owner=CoreObjectDescriptor(id=self.adcm.id, type=orm_object_to_core_type(self.adcm)),
            cause=ConcernCause.CONFIG,
        )
        add_concern_to_object(object_=self.adcm, concern=self.concern)

    def test_list(self):
        test_data = {
            "id": self.adcm.id,
            "name": self.adcm.name,
            "prototype_id": self.adcm.prototype.id,
            "state": self.adcm.state,
            "url": f"http://testserver/api/v1/adcm/{self.adcm.id}/",
        }

        response: Response = self.client.get(reverse(viewname="v1:adcm-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertDictEqual(response.json()["results"][0], test_data)

    def test_list_interface(self):
        test_data = {
            "id": self.adcm.id,
            "name": self.adcm.name,
            "prototype_id": self.adcm.prototype.id,
            "state": self.adcm.state,
            "url": f"http://testserver/api/v1/adcm/{self.adcm.id}/",
            "prototype_version": self.adcm.prototype.version,
            "bundle_id": self.adcm.prototype.bundle_id,
            "config": f"http://testserver/api/v1/adcm/{self.adcm.id}/config/",
            "action": f"http://testserver/api/v1/adcm/{self.adcm.id}/action/",
            "multi_state": [],
            "concerns": [{"id": self.concern.id, "url": f"http://testserver/api/v1/concern/{self.concern.id}/"}],
            "locked": self.adcm.locked,
            "main_info": None,
        }

        response: Response = self.client.get(f"{reverse(viewname='v1:adcm-list')}?view=interface")

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertDictEqual(response.json()["results"][0], test_data)

    def test_retrieve(self):
        test_data = {
            "id": self.adcm.id,
            "name": self.adcm.name,
            "prototype_id": self.adcm.prototype.id,
            "state": self.adcm.state,
            "url": f"http://testserver/api/v1/adcm/{self.adcm.id}/",
            "prototype_version": self.adcm.prototype.version,
            "bundle_id": self.adcm.prototype.bundle_id,
            "config": f"http://testserver/api/v1/adcm/{self.adcm.id}/config/",
            "action": f"http://testserver/api/v1/adcm/{self.adcm.id}/action/",
            "multi_state": [],
            "concerns": [{"id": self.concern.id, "url": f"http://testserver/api/v1/concern/{self.concern.id}/"}],
            "locked": self.adcm.locked,
        }

        response: Response = self.client.get(reverse(viewname="v1:adcm-detail", kwargs={"adcm_pk": self.adcm.id}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(response.json(), test_data)

    def test_retrieve_interface(self):
        test_data = {
            "id": self.adcm.id,
            "name": self.adcm.name,
            "prototype_id": self.adcm.prototype.id,
            "state": "created",
            "url": f"http://testserver/api/v1/adcm/{self.adcm.id}/",
            "prototype_version": self.adcm.prototype.version,
            "bundle_id": self.adcm.prototype.bundle_id,
            "config": f"http://testserver/api/v1/adcm/{self.adcm.id}/config/",
            "action": f"http://testserver/api/v1/adcm/{self.adcm.id}/action/",
            "multi_state": [],
            "concerns": [{"id": self.concern.id, "url": f"http://testserver/api/v1/concern/{self.concern.id}/"}],
            "locked": self.adcm.locked,
            "main_info": None,
        }

        response: Response = self.client.get(
            f"{reverse(viewname='v1:adcm-detail', kwargs={'adcm_pk': self.adcm.id})}?view=interface"
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(response.json(), test_data)
