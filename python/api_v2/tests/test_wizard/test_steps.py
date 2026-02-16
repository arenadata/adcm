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

from copy import deepcopy
from uuid import uuid4

from cm.legacy.services.action_process.schema_validation import (
    ProcessOperationType,
)
from cm.models import Component, ProcessStep, ProcessStepInput, TaskLog
from infra.services import get_config_service
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import APIV2Mixin
from api_v2.tests.setup.base import BaseAPITestCase
from api_v2.tests.test_wizard.helpers import WizardProcessHelpers, render_template


class TestWizardActionProcessSteps(APIV2Mixin, BaseAPITestCase, WizardProcessHelpers):
    def setUp(self) -> None:
        super().setUp()

        get_config_service.cache_clear()

        suffix = uuid4().hex[:8]
        cluster_bundle = self.test_bundles_dir / "wizard_action"
        self.bundle = self.create_bundle(src=cluster_bundle)
        self.cluster_1 = self.create_cluster(
            bundle=self.bundle,
            name=f"cluster_1_{suffix}",
            description=f"cluster_1_{suffix}",
        )
        self.service_1 = self.create_services(["service_1"], cluster=self.cluster_1)[0]
        self.component_1 = Component.objects.get(service=self.service_1, prototype__name="component_1")
        self.process_action_of_cluster = self.get_object_action_with_process(self.cluster_1)

        config_bundle = self.test_bundles_dir / "wizard_config"
        self.config_bundle = self.create_bundle(src=config_bundle)
        self.config_cluster = self.create_cluster(bundle=self.config_bundle, name=f"config_cluster_{suffix}")

    def test_retrieve_config_step_success(self):
        for obj in (self.cluster_1, self.service_1, self.component_1):
            action = self.get_object_action_with_process(obj)
            process = self.start_process(obj, action)
            target_step = ProcessStep.objects.get(
                process_id=process.pk, name="stage1_step1", display_name="Stage1.Step1"
            )
            response_template = self.test_files_dir / "responses" / "wizard_process" / "retrieve_config_step.yml"
            expected_response = render_template(file=response_template, context={"step_id": target_step.pk})

            with self.subTest(f"retrieve config step for {obj}"):
                response = self.get_step_r(obj, action, process.pk, target_step.pk)

                self.assertDictEqual(response.json(), expected_response)

    def test_submit_operation_step_success(self):
        action = self.get_object_action_with_process(self.cluster_1)
        process = self.start_process(self.cluster_1, action)
        initial_sync_key = process.sync_key

        self.advance_two_config_steps(process=process, owner=self.cluster_1, action=action)
        process.refresh_from_db()

        operation_step_id = process.current_step_id

        response = self.submit_step_r(
            self.cluster_1,
            self.process_action_of_cluster.pk,
            process.id,
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {"step_id": operation_step_id, "process_sync_key": process.sync_key},
            },
        )

        response_data = response.json()

        self.assertEqual(response_data["id"], process.id)
        self.assertEqual(response_data["createdAt"], str(process.created_at.isoformat().replace("+00:00", "Z")))
        self.assertEqual(sum(len(stage["steps"]) for stage in response_data["stages"]), process.steps.count())

        process_step = ProcessStep.objects.get(id=operation_step_id)
        expected_spec = [
            {
                "name": "sleep_script",
                "params": {"test_params": ["created"]},
                "script": "wizard_jinja/scripts/sleep.yaml",
                "script_type": "ansible",
                "display_name": "Sleep",
                "state_on_fail": "",
                "allow_to_terminate": False,
                "multi_state_on_fail_set": [],
                "multi_state_on_fail_unset": [],
            }
        ]
        self.assertListEqual(process_step.step_spec, expected_spec)

        task = TaskLog.objects.get(action=self.process_action_of_cluster)
        input_ = ProcessStepInput.objects.get(step_id=operation_step_id)

        self.assertIsNone(input_.configuration)
        self.assertEqual(input_.job_id, task.id)

        process.refresh_from_db()
        self.assertNotEqual(initial_sync_key, process.sync_key)

    def test_operation_validation_fail(self):
        action = self.get_object_action_with_process(self.cluster_1)
        process = self.start_process(self.cluster_1, action)

        with self.subTest("Incorrect method"):
            payload = {"method": "notexist", "params": {"process_sync_key": process.sync_key}}
            response = self.submit_step_r(
                owner=self.cluster_1,
                action=action,
                process_id=process.id,
                data=payload,
                expected_status=HTTP_400_BAD_REQUEST,
            )
            error = response.json()["desc"]
            self.assertIn(
                "Input tag 'notexist' found using 'method' does not match any of the expected tags",
                error,
            )

        with self.subTest("Incorrect payload for complete"):
            payload = {"method": "complete", "params": {}}
            response = self.submit_step_r(
                owner=self.cluster_1,
                action=action,
                process_id=process.id,
                data=payload,
                expected_status=HTTP_400_BAD_REQUEST,
            )
            error = response.json()["desc"]
            self.assertIn("params.process_sync_key", error)
            self.assertIn("Field required [type=missing, input_value={}, input_type=dict]", error)

        with self.subTest("Incorrect payload for submit: missing stepId"):
            payload = {"method": "submit_step", "params": {"processSyncKey": process.sync_key}}
            response = self.submit_step_r(
                owner=self.cluster_1,
                action=action,
                process_id=process.id,
                data=payload,
                expected_status=HTTP_400_BAD_REQUEST,
            )
            error = response.json()["desc"]
            # TODO: not informative error msg
            self.assertIn("5 validation errors for OperationPayloadSchema\npayload.submit_step.params.", error)

        with self.subTest("Incorrect payload for complete: wrong sync key"):
            from uuid import uuid4

            wrong_sync_key = uuid4()
            payload = {"method": "complete", "params": {"processSyncKey": wrong_sync_key}}
            response = self.submit_step_r(
                owner=self.cluster_1,
                action=action,
                process_id=process.id,
                data=payload,
                expected_status=HTTP_409_CONFLICT,
            )
            error = response.json()["desc"]
            self.assertIn(f"Can't find Process #{process.pk} ({str(wrong_sync_key)})", error)

        with self.subTest("Incorrect payload for complete: wrong sync key type"):
            payload = {"method": "complete", "params": {"processSyncKey": "abs"}}
            response = self.submit_step_r(
                owner=self.cluster_1,
                action=action,
                process_id=process.id,
                data=payload,
                expected_status=HTTP_400_BAD_REQUEST,
            )
            error = response.json()["desc"]
            self.assertIn("Input should be a valid UUID", error)

    def test_validation_submit_config(self):
        action = self.get_object_action_with_process(self.config_cluster)
        process = self.start_process(self.config_cluster, action)
        step = process.steps.get(name="first_config_step")

        base_payload = {
            "config": {
                "integer_field": 100,
                "json_not_required": None,
                "agroup": {
                    "str_in_agroup": "new str in agroup value",
                    "json_in_agroup": '{"new": "json", "in": "agroup"}',
                },
            },
            "adcmMeta": {"/agroup": {"isActive": True}},
        }

        with self.subTest("Correct config"):
            self.submit_config_step(
                owner=self.config_cluster,
                action=action,
                process=process,
                step_id=step.id,
                config_payload=base_payload,
            )

            # check json string conversion
            input_ = ProcessStepInput.objects.get(step_id=step.id)
            expected_input = {
                "values": {
                    "integer_field": 100,
                    "json_not_required": None,
                    "agroup": {
                        "str_in_agroup": "new str in agroup value",
                        "json_in_agroup": {"new": "json", "in": "agroup"},
                    },
                },
                "attributes": {"/agroup": {"is_active": True, "is_synced": None}},
            }
            self.assertDictEqual(input_.configuration, expected_input)

        with self.subTest("Without adcmMeta"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            del payload["adcmMeta"]

            self.submit_config_step(
                owner=self.config_cluster,
                action=action,
                process=process,
                step_id=step.id,
                config_payload=payload,
                expected_status=HTTP_409_CONFLICT,
            )

        with self.subTest("With empty adcmMeta"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            payload["adcmMeta"] = {}

            self.submit_config_step(
                owner=self.config_cluster,
                action=action,
                process=process,
                step_id=step.id,
                config_payload=payload,
                expected_status=HTTP_409_CONFLICT,
            )

        with self.subTest("With empty /agroup meta"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            payload["adcmMeta"]["/agroup"] = {}

            self.submit_config_step(
                owner=self.config_cluster,
                action=action,
                process=process,
                step_id=step.id,
                config_payload=payload,
                expected_status=HTTP_400_BAD_REQUEST,
            )

        with self.subTest("Without required field"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            del payload["config"]["integer_field"]

            self.submit_config_step(
                owner=self.config_cluster,
                action=action,
                process=process,
                step_id=step.id,
                config_payload=payload,
                expected_status=HTTP_409_CONFLICT,
            )

    def test_404_on_not_exist_different_parts(self):
        action = self.get_object_action_with_process(self.cluster_1)
        process = self.start_process(self.cluster_1, action)
        not_existing_process_id = 1_000_000
        not_existing_step_id = 1_000_000

        with self.subTest("get-process-not-exist"):
            response = self.get_process_r(
                self.cluster_1, action, not_existing_process_id, expected_status=HTTP_404_NOT_FOUND
            )
            self.assertEqual(response.json()["code"], "ACTION_PROCESS_NOT_FOUND")

        with self.subTest("get-step-not-exist-process-exist"):
            response = self.get_step_r(
                self.cluster_1, action, process.pk, not_existing_step_id, expected_status=HTTP_404_NOT_FOUND
            )
            self.assertEqual(response.json()["code"], "ACTION_PROCESS_STEP_NOT_FOUND")

        with self.subTest("get-step-not-exist-process-not-exist"):
            response = self.get_step_r(
                self.cluster_1,
                action,
                not_existing_process_id,
                not_existing_step_id,
                expected_status=HTTP_404_NOT_FOUND,
            )
            self.assertEqual(response.json()["code"], "ACTION_PROCESS_NOT_FOUND")

        # TODO fix during ADCM-7753
        # with self.subTest("get-process-exist-wrong-object"):
        #    response = self.get_process_r(self.service_1, action, process.id, expected_status=HTTP_404_NOT_FOUND)
        #    self.assertEqual(response.json()["code"], "ACTION_PROCESS_NOT_FOUND")

        # with self.subTest("get-step-exist-process-exist-wrong-object"):
        #    response = self.get_step_r(
        #        self.service_1, action, process.id, process.steps.first().pk, expected_status=HTTP_404_NOT_FOUND
        #    )
        #    self.assertEqual(response.json()["code"], "ACTION_PROCESS_NOT_FOUND")

    def test_submit_non_current_step(self):
        action = self.get_object_action_with_process(self.cluster_1)
        process = self.start_process(self.cluster_1, action)
        target_step = ProcessStep.objects.get(process_id=process.id, name="stage3_step1", display_name="Stage3.Step1")

        process_sync_key = process.sync_key
        payload = {
            "method": "submit_step",
            "params": {"processSyncKey": process_sync_key, "stepId": target_step.id},
        }

        response = self.submit_step_r(
            owner=self.cluster_1,
            action=action,
            process_id=process.id,
            data=payload,
            expected_status=HTTP_409_CONFLICT,
        )

        self.assertEqual(response.json()["code"], "ACTION_PROCESS_OPERATION_CONFLICT")
        self.assertEqual(response.json()["desc"], "Only current step can be submitted")

    def test_submit_previously_submitted_step(self):
        action = self.get_object_action_with_process(self.cluster_1)
        process = self.start_process(self.cluster_1, action)
        step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")

        payload = {
            "method": "submit_step",
            "params": {
                "configuration": {
                    "config": {
                        "integer_field": 100,
                        "string_field": "string",
                    },
                    "adcmMeta": {},
                },
                "processSyncKey": process.sync_key,
                "stepId": step.id,
            },
        }

        response = self.submit_step_r(owner=self.cluster_1, action=action, process_id=process.id, data=payload)

        process.refresh_from_db()
        payload["params"]["processSyncKey"] = process.sync_key

        response = self.submit_step_r(
            owner=self.cluster_1,
            action=action,
            process_id=process.id,
            data=payload,
            expected_status=HTTP_409_CONFLICT,
        )

        self.assertEqual(response.json()["code"], "ACTION_PROCESS_OPERATION_CONFLICT")
        self.assertEqual(response.json()["desc"], "Only current step can be submitted")
