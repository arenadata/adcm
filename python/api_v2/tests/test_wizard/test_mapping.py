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
from adcm.tests.client import ADCMTestClient, APINode
from cm.legacy.services.action_process.schema_validation import ProcessOperationType
from cm.legacy.services.action_process.types import ProcessStepState
from cm.models import (
    Action,
    Cluster,
    Component,
    MaintenanceMode,
    Process,
    ProcessStep,
)
from infra.services import get_config_service
from init_db import init
from rbac.upgrade.role import init_roles
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT
from rest_framework.test import APITestCase

from api_v2.tests.base import APIV2Mixin, TestUtilsMixin


class TestWizardMapping(APITestCase, ParallelReadyTestCase, APIV2Mixin, TestUtilsMixin):
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
        cluster_bundle = self.create_bundle(src=self.test_bundles_dir / "wizard_action")
        provider_bundle = self.create_bundle(src=self.test_bundles_dir / "provider")

        self.cluster = self.create_cluster(bundle=cluster_bundle, name="test_cluster")
        self.service = self.create_services(names=["service_1"], cluster=self.cluster)[0]
        self.component_1 = Component.objects.get(service=self.service, prototype__name="component_1")
        # existence check, needs for mm distribution
        Component.objects.get(service=self.service, prototype__name="component_2")

        self.provider = self.create_provider(bundle=provider_bundle, name="test_provider")
        self.host_1 = self.create_host(provider=self.provider, name="test-host-1", cluster=self.cluster)
        self.host_2 = self.create_host(provider=self.provider, name="test-host-2", cluster=self.cluster)

        self.action = Action.objects.get(name="wizard_with_mapping_only", prototype_id=self.cluster.prototype_id)

    def init_process(self, cluster: Cluster, action: Action) -> tuple[Process, APINode]:
        action_endpoint = self.client.v2[cluster, "actions", action]
        response = (action_endpoint / "processes").post(data={})
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        process = Process.objects.get(pk=response.json()["id"])
        operation_endpoint = action_endpoint / "processes" / process / "operation"

        return process, operation_endpoint

    def check_submit_mapping_step_response(
        self,
        process: Process,
        delta: dict,
        operation_endpoint: APINode,
        expected_code: int,
        step_name: str = "step_1_mapping",
    ):
        process.refresh_from_db()

        step_mapping = ProcessStep.objects.get(process=process, name=step_name)
        self.assertEqual(step_mapping.state, ProcessStepState.CREATED.value)

        response = operation_endpoint.post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "processSyncKey": process.sync_key,
                    "stepId": step_mapping.id,
                    "hostComponentMapDelta": delta,
                },
            }
        )
        self.assertEqual(response.status_code, expected_code)

        if expected_code != HTTP_200_OK:
            expected_response = {
                "code": "INVALID_HC_HOST_IN_MM",
                "level": "error",
                "desc": "You can't save hc with hosts in maintenance mode",
            }
            self.assertDictEqual(response.json(), expected_response)

        return response

    def test_adcm_7530_add_host_in_mm_fail(self):
        process, operation_endpoint = self.init_process(cluster=self.cluster, action=self.action)
        self.set_maintenance_mode(obj=self.host_1, value=MaintenanceMode.ON)

        self.check_mm_is_on_only_for(obj=self.host_1, cluster_id=self.cluster.id)
        self.check_submit_mapping_step_response(
            process=process,
            delta={"add": [{"hostId": self.host_1.id, "componentId": self.component_1.id}]},
            operation_endpoint=operation_endpoint,
            expected_code=HTTP_409_CONFLICT,
        )

    def test_adcm_7530_remove_host_in_mm_success(self):
        process, operation_endpoint = self.init_process(cluster=self.cluster, action=self.action)
        self.create_mapping(
            cluster=self.cluster,
            entries=[
                (self.host_1, self.component_1),
                (self.host_2, self.component_1),
            ],
        )
        self.set_maintenance_mode(obj=self.host_2, value=MaintenanceMode.ON)

        self.check_mm_is_on_only_for(obj=self.host_2, cluster_id=self.cluster.id)
        self.check_submit_mapping_step_response(
            process=process,
            delta={"remove": [{"hostId": self.host_2.id, "componentId": self.component_1.id}]},
            operation_endpoint=operation_endpoint,
            expected_code=HTTP_200_OK,
        )

    def test_adcm_7530_add_to_component_in_mm_success(self):
        process, operation_endpoint = self.init_process(cluster=self.cluster, action=self.action)
        self.set_maintenance_mode(obj=self.component_1, value=MaintenanceMode.ON)

        self.check_mm_is_on_only_for(obj=self.component_1, cluster_id=self.cluster.id)
        self.check_submit_mapping_step_response(
            process=process,
            delta={"add": [{"hostId": self.host_2.id, "componentId": self.component_1.id}]},
            operation_endpoint=operation_endpoint,
            expected_code=HTTP_200_OK,
        )

    def test_adcm_7530_remove_from_component_in_mm_success(self):
        process, operation_endpoint = self.init_process(cluster=self.cluster, action=self.action)
        self.create_mapping(
            cluster=self.cluster,
            entries=[
                (self.host_1, self.component_1),
                (self.host_2, self.component_1),
            ],
        )
        self.set_maintenance_mode(obj=self.component_1, value=MaintenanceMode.ON)

        self.check_mm_is_on_only_for(obj=self.component_1, cluster_id=self.cluster.id)
        self.check_submit_mapping_step_response(
            process=process,
            delta={"remove": [{"hostId": self.host_1.id, "componentId": self.component_1.id}]},
            operation_endpoint=operation_endpoint,
            expected_code=HTTP_200_OK,
        )

    def test_adcm_7530_service_state_does_not_affects_success(self):
        process, operation_endpoint = self.init_process(cluster=self.cluster, action=self.action)
        self.create_mapping(
            cluster=self.cluster,
            entries=[
                (self.host_1, self.component_1),
            ],
        )

        self.service.state = "not created"
        self.service.save(update_fields=["state"])

        self.check_mm_is_on_only_for(obj=None, cluster_id=self.cluster.id)
        self.check_submit_mapping_step_response(
            process=process,
            delta={
                "add": [{"hostId": self.host_2.id, "componentId": self.component_1.id}],
                "remove": [{"hostId": self.host_1.id, "componentId": self.component_1.id}],
            },
            operation_endpoint=operation_endpoint,
            expected_code=HTTP_200_OK,
        )
