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


from cm.legacy.services.action_process.schema_validation import ProcessOperationType
from cm.legacy.services.action_process.types import ProcessStepState
from cm.models import (
    Action,
    Component,
    MaintenanceMode,
    ProcessStep,
)
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_409_CONFLICT

from api_v2.tests.base import APIV2Mixin, TestUtilsMixin
from api_v2.tests.setup.base import BaseAPITestCase


class TestWizardMapping(BaseAPITestCase, APIV2Mixin, TestUtilsMixin):
    def setUp(self):
        super().setUp()

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

        self.process = self.start_process(owner=self.cluster, action=self.action)
        self.step = ProcessStep.objects.get(process=self.process, name="step_1_mapping", state=ProcessStepState.CREATED)

    def expect_submit_mapping_step_succeed(self, delta: dict) -> Response:
        return self.submit_mapping_step_r(delta=delta, expected_status=HTTP_200_OK)

    def submit_mapping_step_r(self, delta: dict, expected_status: int) -> Response:
        data = {
            "method": ProcessOperationType.SUBMIT,
            "params": {
                "processSyncKey": self.process.sync_key,
                "stepId": self.step.pk,
                "hostComponentMapDelta": delta,
            },
        }
        return self.submit_step_r(
            owner=self.cluster,
            action=self.action,
            process_id=self.process.pk,
            data=data,
            expected_status=expected_status,
        )

    def set_service_state_not_created(self) -> None:
        self.service.state = "not created"
        self.service.save(update_fields=["state"])

    def test_adcm_7530_add_host_in_mm_fail(self):
        delta = {"add": [{"hostId": self.host_1.pk, "componentId": self.component_1.pk}]}
        expected_response = {
            "code": "INVALID_HC_HOST_IN_MM",
            "level": "error",
            "desc": "You can't save hc with hosts in maintenance mode",
        }

        self.set_maintenance_mode(obj=self.host_1, value=MaintenanceMode.ON)
        self.check_mm_is_on_only_for(obj=self.host_1, cluster_id=self.cluster.pk)

        response = self.submit_mapping_step_r(delta=delta, expected_status=HTTP_409_CONFLICT)

        self.assertDictEqual(response.json(), expected_response)

    def test_adcm_7530_remove_host_in_mm_success(self):
        delta = {"remove": [{"hostId": self.host_2.pk, "componentId": self.component_1.pk}]}

        self.create_mapping(
            cluster=self.cluster,
            entries=[(self.host_1, self.component_1), (self.host_2, self.component_1)],
        )
        self.set_maintenance_mode(obj=self.host_2, value=MaintenanceMode.ON)
        self.check_mm_is_on_only_for(obj=self.host_2, cluster_id=self.cluster.pk)

        self.expect_submit_mapping_step_succeed(delta=delta)

    def test_adcm_7530_add_to_component_in_mm_success(self):
        delta = {"add": [{"hostId": self.host_2.pk, "componentId": self.component_1.pk}]}

        self.set_maintenance_mode(obj=self.component_1, value=MaintenanceMode.ON)
        self.check_mm_is_on_only_for(obj=self.component_1, cluster_id=self.cluster.pk)

        self.expect_submit_mapping_step_succeed(delta=delta)

    def test_adcm_7530_remove_from_component_in_mm_success(self):
        delta = {"remove": [{"hostId": self.host_1.pk, "componentId": self.component_1.pk}]}

        self.create_mapping(
            cluster=self.cluster,
            entries=[
                (self.host_1, self.component_1),
                (self.host_2, self.component_1),
            ],
        )
        self.set_maintenance_mode(obj=self.component_1, value=MaintenanceMode.ON)
        self.check_mm_is_on_only_for(obj=self.component_1, cluster_id=self.cluster.pk)

        self.expect_submit_mapping_step_succeed(delta=delta)

    def test_adcm_7530_service_state_does_not_affects_success(self):
        delta = {
            "add": [{"hostId": self.host_2.pk, "componentId": self.component_1.pk}],
            "remove": [{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        }

        self.create_mapping(
            cluster=self.cluster,
            entries=[(self.host_1, self.component_1)],
        )
        self.set_service_state_not_created()
        self.check_mm_is_on_only_for(obj=None, cluster_id=self.cluster.pk)

        self.expect_submit_mapping_step_succeed(delta=delta)
