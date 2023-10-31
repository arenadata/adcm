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
from unittest.mock import patch

from api_v2.tests.base import BaseAPITestCase
from cm.issue import add_concern_to_object
from cm.models import Action, ConcernType, MaintenanceMode, ServiceComponent
from cm.tests.utils import gen_concern_item
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_405_METHOD_NOT_ALLOWED


class TestComponentAPI(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
        self.component_1 = ServiceComponent.objects.get(
            prototype__name="component_1", service=self.service_1, cluster=self.cluster_1
        )
        self.component_2_to_delete = ServiceComponent.objects.get(
            prototype__name="component_2", service=self.service_1, cluster=self.cluster_1
        )
        self.action_1 = Action.objects.get(name="action_1_comp_1")

    def test_list(self):
        response = self.client.get(
            path=reverse(
                "v2:component-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                "v2:component-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.component_1.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.component_1.pk)

    def test_adcm_4526_retrieve_concerns_regardless_owner_success(self):
        concern_1 = gen_concern_item(ConcernType.LOCK, owner=self.cluster_1)
        concern_2 = gen_concern_item(ConcernType.ISSUE, owner=self.service_1)
        concern_3 = gen_concern_item(ConcernType.FLAG, owner=self.component_1)
        add_concern_to_object(object_=self.component_1, concern=concern_1)
        add_concern_to_object(object_=self.component_1, concern=concern_2)
        add_concern_to_object(object_=self.component_1, concern=concern_3)

        response = self.client.get(
            path=reverse(
                "v2:component-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.component_1.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 3)

    def test_delete_success(self):
        response = self.client.delete(
            path=reverse(
                "v2:component-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.component_1.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_405_METHOD_NOT_ALLOWED)

    def test_action_list_success(self):
        response = self.client.get(
            path=reverse(
                "v2:component-action-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_action_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                "v2:component-action-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.action_1.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_action_run_success(self):
        with patch(
            "api_v2.action.views.start_task",
            return_value=self.create_task_log(object_=self.component_1, action=self.action_1),
        ):
            response = self.client.post(
                path=reverse(
                    "v2:component-action-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "component_pk": self.component_1.pk,
                        "pk": self.action_1.pk,
                    },
                ),
                data={"hostComponent_map": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_change_mm(self):
        response = self.client.post(
            path=reverse(
                "v2:component-maintenance-mode",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.component_1.pk,
                },
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
