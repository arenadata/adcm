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
from cm.legacy.services.action_process.types import ProcessState, ProcessStepState
from cm.models import (
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    Process,
    ProcessStep,
    Service,
)
from django.contrib.contenttypes.models import ContentType
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from tests.client import APINode
from tests.suites import ADCMDjangoAPISuite

from api_v2.tests.base import APIV2Mixin


class TestWizardOnAHG(ADCMDjangoAPISuite, APIV2Mixin):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cluster_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "wizard_action")
        provider_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider")

        cls.cluster = cls.uc.add_cluster(bundle=cluster_bundle, name="test_cluster")
        cls.service = cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cluster)[0]
        cls.component = Component.objects.get(service=cls.service, prototype__name="component_1")

        cls.provider = cls.uc.add_provider(bundle=provider_bundle, name="test_provider")
        cls.host = cls.uc.add_host(provider=cls.provider, name="test-host", cluster=cls.cluster)

        cls.expected_step_spec = {
            "step_1_config": [
                {
                    "groups": {},
                    "hierarchy": {
                        "child_groups": {},
                        "fields": ["float", "step_variant_from_config"],
                        "rule": "all",
                    },
                    "parameters": {
                        "/float": {
                            "extra": {
                                "description": "",
                                "display_name": "float",
                                "edit_rule": {"writable": "any"},
                                "ui_options": {},
                            },
                            "identifier": {"full": "/float", "name": "float"},
                            "is_desyncable": False,
                            "is_float": True,
                            "is_required": False,
                            "max": None,
                            "min": None,
                            "type": "number",
                        },
                        "/step_variant_from_config": {
                            "extra": {
                                "description": "",
                                "display_name": "step_variant_from_config",
                                "edit_rule": {"writable": "any"},
                                "ui_options": {},
                            },
                            "identifier": {"full": "/step_variant_from_config", "name": "step_variant_from_config"},
                            "is_desyncable": False,
                            "is_required": False,
                            "is_strict": True,
                            "payload": {"args": None, "name": "group1/list_field", "strict": True, "type": "config"},
                            "source": "config",
                            "type": "variant",
                        },
                    },
                },
                {
                    "activation": {},
                    "selection": {},
                    "values": {
                        "/float": 0.1,
                        "/step_variant_from_config": None,
                    },
                },
            ],
            "step_2_mapping": [
                {"service": cls.component.service.name, "component": cls.component.name, "operation": "remove"}
            ],
            "step_3_operation": [
                {
                    "name": "sleep_script",
                    "params": {},
                    "script": "wizard_jinja/scripts/sleep.yaml",
                    "script_type": "ansible",
                    "display_name": "Sleep",
                    "state_on_fail": "",
                    "allow_to_terminate": False,
                    "multi_state_on_fail_set": [],
                    "multi_state_on_fail_unset": [],
                }
            ],
        }

    def check_wizard_action_retrieval(self, ahg: ActionHostGroup, action: Action) -> None:
        response = self.client.v2[ahg, "actions", action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(response.json()["processes"], [])

    def check_step_retrieval(self, name: str, process: Process, action_endpoint: APINode) -> None:
        target_step = ProcessStep.objects.get(process=process, name=name)
        response = (action_endpoint / "processes" / process / "steps" / target_step).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        response = response.json()
        self.assertEqual(response["id"], target_step.id)
        self.assertEqual(response["name"], name)
        self.assertEqual(response["state"], "created")

    def check_process_creation(self, ahg: ActionHostGroup, action: Action) -> tuple[Process, APINode]:
        owner_concerns = ConcernItem.objects.filter(
            owner_id=ahg.object.id,
            owner_type=ContentType.objects.get_for_model(ahg.object),
            cause=ConcernCause.CONFIGURING_PROCESS,
        )
        self.assertEqual(owner_concerns.count(), 0)

        action_endpoint = self.client.v2[ahg, "actions", action]

        response = (action_endpoint / "processes").post(data={})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        process_id = response.json()["id"]

        response = action_endpoint.get()
        processes = response.json()["processes"]
        self.assertEqual(len(processes), 1)
        self.assertEqual(processes[0]["id"], process_id)

        owner_concerns = ConcernItem.objects.filter(
            owner_id=ahg.object.id,
            owner_type=ContentType.objects.get_for_model(ahg.object),
            cause=ConcernCause.CONFIGURING_PROCESS,
        )
        self.assertEqual(owner_concerns.count(), 1)

        process = Process.objects.get(id=process_id)
        self.assertEqual(process.state, ProcessState.CREATED.value)

        return process, action_endpoint

    def check_first_config_step(self, process: Process, name: str, operation_endpoint: APINode) -> None:
        process.refresh_from_db()

        step_1_config = ProcessStep.objects.get(process=process, name=name)
        self.assertEqual(step_1_config.state, ProcessStepState.CREATED.value)
        self.assertListEqual(step_1_config.step_spec, self.expected_step_spec[step_1_config.name])

        response = operation_endpoint.post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "processSyncKey": process.sync_key,
                    "stepId": step_1_config.id,
                    "configuration": {
                        "config": {"float": 0.4, "step_variant_from_config": "entry1"},
                        "adcmMeta": {},
                    },
                },
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        step_1_config.refresh_from_db()
        self.assertEqual(step_1_config.state, ProcessStepState.COMPLETED)

    def check_second_mapping_step(self, process: Process, name: str, operation_endpoint: APINode) -> None:
        process.refresh_from_db()

        step_2_mapping = ProcessStep.objects.get(process=process, name=name)
        self.assertListEqual(step_2_mapping.step_spec, self.expected_step_spec[step_2_mapping.name])
        self.assertEqual(step_2_mapping.state, ProcessStepState.CREATED.value)

        response = operation_endpoint.post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "processSyncKey": process.sync_key,
                    "stepId": step_2_mapping.id,
                    "hostComponentMapDelta": {"remove": [{"hostId": self.host.id, "componentId": self.component.id}]},
                },
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        step_2_mapping.refresh_from_db()
        self.assertEqual(step_2_mapping.state, ProcessStepState.COMPLETED)

    def check_third_operation_step(self, process: Process, name: str, operation_endpoint: APINode) -> None:
        process.refresh_from_db()

        step_3_operation = ProcessStep.objects.get(process=process, name=name)
        self.assertListEqual(step_3_operation.step_spec, self.expected_step_spec[step_3_operation.name])
        self.assertEqual(step_3_operation.state, ProcessStepState.CREATED.value)

        response = operation_endpoint.post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {"processSyncKey": process.sync_key, "stepId": step_3_operation.id},
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        launched_task = self.task_runner.expect_task_launched()
        self.task_runner.run_task(launched_task.id)

        step_3_operation.refresh_from_db()
        self.assertEqual(step_3_operation.state, ProcessStepState.COMPLETED)

    def check_complete_process(self, process: Process, ahg: ActionHostGroup, operation_endpoint: APINode):
        owner_concerns = ConcernItem.objects.filter(
            owner_id=ahg.object.id,
            owner_type=ContentType.objects.get_for_model(ahg.object),
            cause=ConcernCause.CONFIGURING_PROCESS,
        )
        self.assertEqual(owner_concerns.count(), 1)

        process.refresh_from_db()
        response = operation_endpoint.post(
            data={"method": ProcessOperationType.COMPLETE, "params": {"processSyncKey": process.sync_key}}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        owner_concerns = ConcernItem.objects.filter(
            owner_id=ahg.object.id,
            owner_type=ContentType.objects.get_for_model(ahg.object),
            cause=ConcernCause.CONFIGURING_PROCESS,
        )
        self.assertEqual(owner_concerns.count(), 0)

        process.refresh_from_db()
        self.assertEqual(process.state, ProcessState.COMPLETED.value)

    def check_run_wizard_final_action(self, process: Process, action_endpoint: APINode) -> None:
        response = (action_endpoint / "run").post(data={"process": {"id": process.id}})

        self.assertEqual(response.status_code, HTTP_200_OK)

        self.task_runner.expect_task_launched()

    def _test_adcm_7584_wizard_happy_path_on_ahg(self, object_: Cluster | Service | Component, action: Action):
        host = self.create_host(provider=self.provider, name="test-host-cluster", cluster=self.cluster)
        self.create_mapping(cluster=self.cluster, entries=[(self.host, self.component), (host, self.component)])
        ahg = self.create_action_host_group(
            owner=object_, name=f"ahg_for_{object_.__class__.__name__.lower()}", hosts=[self.host, host]
        )

        self.check_wizard_action_retrieval(ahg=ahg, action=action)
        process, action_endpoint = self.check_process_creation(ahg=ahg, action=action)

        operation_endpoint = action_endpoint / "processes" / process / "operation"
        step_1_name, step_2_name, step_3_name = "step_1_config", "step_2_mapping", "step_3_operation"

        self.check_step_retrieval(name=step_1_name, process=process, action_endpoint=action_endpoint)
        self.check_first_config_step(process=process, name=step_1_name, operation_endpoint=operation_endpoint)

        self.check_step_retrieval(name=step_2_name, process=process, action_endpoint=action_endpoint)
        self.check_second_mapping_step(process=process, name=step_2_name, operation_endpoint=operation_endpoint)

        self.check_step_retrieval(name=step_3_name, process=process, action_endpoint=action_endpoint)
        self.check_third_operation_step(process=process, name=step_3_name, operation_endpoint=operation_endpoint)

        self.check_complete_process(process=process, ahg=ahg, operation_endpoint=operation_endpoint)
        self.check_run_wizard_final_action(process=process, action_endpoint=action_endpoint)

    def test_adcm_7584_wizard_on_ahg_cluster(self):
        wizard_cluster_action = Action.objects.get(name="wizard_cluster_action", prototype=self.cluster.prototype)
        self._test_adcm_7584_wizard_happy_path_on_ahg(object_=self.cluster, action=wizard_cluster_action)

    def test_adcm_7584_wizard_on_ahg_service(self):
        wizard_service_action = Action.objects.get(name="wizard_service_action", prototype=self.service.prototype)
        self._test_adcm_7584_wizard_happy_path_on_ahg(object_=self.service, action=wizard_service_action)

    def test_adcm_7584_wizard_on_ahg_component(self):
        wizard_component_action = Action.objects.get(name="wizard_component_action", prototype=self.component.prototype)
        self._test_adcm_7584_wizard_happy_path_on_ahg(object_=self.component, action=wizard_component_action)
