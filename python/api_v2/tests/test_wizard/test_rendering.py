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

from pathlib import Path

from adcm.dependencies import prepare_container
from adcm.tests.base import ParallelReadyTestCase
from adcm.tests.client import ADCMTestClient
from cm.models import (
    Action,
    Cluster,
)
from infra.services import get_config_service
from init_db import init
from rbac.upgrade.role import init_roles
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.test import APITestCase

from api_v2.tests.base import APIV2Mixin


class TestImplementDescription(APITestCase, ParallelReadyTestCase, APIV2Mixin):
    client: ADCMTestClient
    client_class = ADCMTestClient

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        prepare_container.cache_clear()
        get_config_service.cache_clear()  # TODO: ADCM-7513
        cls.test_bundles_dir = Path(__file__).parent.parent / "bundles"
        init_roles()
        init()

    def setUp(self):
        self.client.login(username="admin", password="admin")
        self.cluster_bundle = self.create_bundle(src=self.test_bundles_dir / "wizard_rendering_description")
        self.step_descr_mapping = {
            "action_step_config": "Config step description",
            "action_step_operation": "Operational step description",
            "action_step_mapping": "Mapping step description",
            "action_no_desc": "",
        }
        self.stage_descr_mapping = {
            "action_step_config": "Stage description",
            "action_no_desc": "",
        }

    def start_process(self, obj: Cluster, action_id: int) -> int:
        process_endpoint = self.client.v2[obj, "actions", action_id, "processes"]
        response = process_endpoint.post(data={})
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())
        return response.json()["id"]

    def get_process_spec(self, obj: Cluster, action_id: int, process_id: int) -> dict:
        steps_endpoint = self.client.v2[obj, "actions", action_id, "processes", process_id]
        response = steps_endpoint.get()
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())
        return response.json()

    def test_rendering_step_description(self):
        for action_name, description in self.step_descr_mapping.items():
            with self.subTest(f"Check the step description field for '{action_name}' case"):
                cluster = self.create_cluster(bundle=self.cluster_bundle, name=f"test_cluster_with_{action_name}")
                action = Action.objects.get(name=action_name, prototype=cluster.prototype)
                process_id = self.start_process(cluster, action.pk)
                step_data = [
                    step
                    for stage in self.get_process_spec(cluster, action.pk, process_id)["stages"]
                    for step in stage["steps"]
                ][0]
                step_type, step_id = step_data["type"], step_data["id"]

                with self.subTest(f"Check the step's description field from the process '{process_id}'"):
                    self.assertEqual(step_data["description"], description)

                with self.subTest(f"Check the description from spec of the '{step_type}' step"):
                    step_endpoint = self.client.v2[
                        cluster, "actions", action.pk, "processes", process_id, "steps", step_id
                    ]
                    response = step_endpoint.get()
                    self.assertEqual(response.status_code, HTTP_200_OK, response.json())
                    self.assertEqual(step_data["description"], description)

    def test_rendering_stage_description(self):
        for action_name, description in self.stage_descr_mapping.items():
            with self.subTest(f"Check the stage description field for '{action_name}' case"):
                cluster = self.create_cluster(bundle=self.cluster_bundle, name=f"test_cluster_with_{action_name}")
                action = Action.objects.get(name=action_name, prototype=cluster.prototype)
                process_id = self.start_process(cluster, action.pk)
                stage_data = self.get_process_spec(cluster, action.pk, process_id)["stages"][0]

                with self.subTest(f"Check the step's description field from the process '{process_id}'"):
                    self.assertEqual(stage_data["description"], description)
