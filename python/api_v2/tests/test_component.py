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

from cm.issue import add_concern_to_object
from cm.models import Action, Component, ConcernType, MaintenanceMode
from cm.tests.mocks.task_runner import RunTaskMock
from cm.tests.utils import gen_concern_item
from rest_framework.status import HTTP_200_OK, HTTP_405_METHOD_NOT_ALLOWED, HTTP_409_CONFLICT

from api_v2.tests.base import BaseAPITestCase


class TestComponentAPI(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1 = Component.objects.get(
            prototype__name="component_1", service=self.service_1, cluster=self.cluster_1
        )
        self.component_2_to_delete = Component.objects.get(
            prototype__name="component_2", service=self.service_1, cluster=self.cluster_1
        )
        self.action_1 = Action.objects.get(name="action_1_comp_1", prototype=self.component_1.prototype)

    def test_list(self):
        response = self.client.v2[self.service_1, "components"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_retrieve_success(self):
        response = self.client.v2[self.component_1].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.component_1.pk)

    def test_adcm_4526_retrieve_concerns_regardless_owner_success(self):
        concern_1 = gen_concern_item(ConcernType.LOCK, owner=self.cluster_1)
        concern_2 = gen_concern_item(ConcernType.ISSUE, owner=self.service_1)
        concern_3 = gen_concern_item(ConcernType.FLAG, owner=self.component_1)
        add_concern_to_object(object_=self.component_1, concern=concern_1)
        add_concern_to_object(object_=self.component_1, concern=concern_2)
        add_concern_to_object(object_=self.component_1, concern=concern_3)

        response = self.client.v2[self.component_1].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["concerns"]), 3)

    def test_delete_success(self):
        response = self.client.v2[self.component_1].delete()

        self.assertEqual(response.status_code, HTTP_405_METHOD_NOT_ALLOWED)

    def test_action_list_success(self):
        response = self.client.v2[self.component_1, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_action_retrieve_success(self):
        response = self.client.v2[self.component_1, "actions", self.action_1].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_action_run_success(self):
        with RunTaskMock() as run_task:
            response = self.client.v2[self.component_1, "actions", self.action_1, "run"].post(
                data={"hostComponent_map": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], run_task.target_task.id)
        self.assertEqual(run_task.target_task.status, "created")

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")


class TestComponentMaintenanceMode(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1_cl_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1_cl_1 = Component.objects.get(
            prototype__name="component_1", service=self.service_1_cl_1, cluster=self.cluster_1
        )

        self.service_cl_2 = self.add_services_to_cluster(service_names=["service"], cluster=self.cluster_2).get()
        self.component_cl_1 = Component.objects.get(
            prototype__name="component", service=self.service_cl_2, cluster=self.cluster_2
        )

    def test_change_mm_success(self):
        response = self.client.v2[self.component_1_cl_1, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_chamge_mm_not_available_fail(self):
        response = self.client.v2[self.component_cl_1, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "MAINTENANCE_MODE_NOT_AVAILABLE",
                "level": "error",
                "desc": "Component does not support maintenance mode",
            },
        )
