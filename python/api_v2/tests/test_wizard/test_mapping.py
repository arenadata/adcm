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
from typing import Literal
from uuid import uuid4

from cm.legacy.services.action_process.operations import find_current_and_last_completed_steps
from cm.legacy.services.action_process.schema_validation import ProcessOperationType
from cm.legacy.services.action_process.types import ProcessStepState
from cm.models import Action, Component, Host, Process, ProcessStep, ProcessStepInput
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT
from tests.client import APINode
from tests.deprecated import BusinessLogicMixin
from tests.suites import ADCMDjangoAPISuite

from api_v2.tests.base import APIV2Mixin
from api_v2.tests.test_wizard.helpers import WizardProcessHelpers


class TestWizardActionProcessMapping(ADCMDjangoAPISuite, APIV2Mixin, WizardProcessHelpers, BusinessLogicMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        suffix = uuid4().hex[:8]
        mapping_bundle = cls.test_bundles_dir / "wizard_mapping"
        cls.mapping_bundle = cls.uc.upload_bundle(src=mapping_bundle)
        cls.cluster_3 = cls.uc.add_cluster(
            bundle=cls.mapping_bundle,
            name=f"cluster_3_{suffix}",
            description=f"cluster_3_{suffix}",
        )

        provider_bundle_path = cls.test_bundles_dir / "provider"
        cls.provider_bundle = cls.uc.upload_bundle(src=provider_bundle_path)
        cls.provider = cls.uc.add_provider(
            bundle=cls.provider_bundle,
            name=f"provider_{suffix}",
            description=f"provider_{suffix}",
        )

        bundle_hc_restrictions_dir = cls.test_bundles_dir / "wizard_mapping_restrictions"
        bundle = cls.uc.upload_bundle(src=bundle_hc_restrictions_dir)
        cls.cluster_with_mapping_restrictions = cls.uc.add_cluster(
            bundle=bundle, name=f"cluster with mapping restrictions {suffix}"
        )

    def test_submit_mapping_success(self):
        self.create_services(["service_1", "service_2", "service_3"], cluster=self.cluster_3)
        component_1_s_1 = Component.objects.filter(service__prototype__name="service_1", cluster=self.cluster_3).first()
        component_1_s_2 = Component.objects.filter(service__prototype__name="service_2", cluster=self.cluster_3).first()
        component_1_s_3 = Component.objects.filter(service__prototype__name="service_3", cluster=self.cluster_3).first()
        host_1 = self.create_host(provider=self.provider, name="host-1", cluster=self.cluster_3)
        host_2 = self.create_host(provider=self.provider, name="host-2", cluster=self.cluster_3)
        host_3 = self.create_host(provider=self.provider, name="host-3", cluster=self.cluster_3)

        action = self.get_object_action_with_process(self.cluster_3)
        process = self.start_process(self.cluster_3, action)

        config = {"integer_field": 10, "string_field": "string"}

        self.submit_step(
            owner=self.cluster_3,
            action=action,
            process_id=process.id,
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "processSyncKey": process.sync_key,
                    "stepId": process.current_step_id,
                    "configuration": {"config": config, "adcmMeta": {}},
                },
            },
        )

        process.refresh_from_db()

        current_step_id = process.current_step_id

        with self.subTest("Submit mapping not component in step spec (fail)"):
            host_component_map_delta = {
                "add": [
                    {"hostId": host_1.pk, "componentId": component_1_s_3.pk},
                ],
            }

            response = self.client.v2[self.cluster_3, "actions", action.pk, "processes", process.id, "operation"].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {
                        "step_id": current_step_id,
                        "process_sync_key": process.sync_key,
                        "host_component_map_delta": host_component_map_delta,
                    },
                }
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        with self.subTest("Submit mapping not specified in step spec (fail)"):
            host_component_map_delta = {
                "add": [
                    {"hostId": host_1.pk, "componentId": component_1_s_3.pk},
                ],
            }

            response = self.client.v2[self.cluster_3, "actions", action.pk, "processes", process.id, "operation"].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {
                        "step_id": current_step_id,
                        "process_sync_key": process.sync_key,
                        "host_component_map_delta": host_component_map_delta,
                    },
                }
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        with self.subTest("Submit 2 mapping steps"):
            host_component_map_delta = {
                "add": [
                    {"hostId": host_1.pk, "componentId": component_1_s_1.pk},
                    {"hostId": host_2.pk, "componentId": component_1_s_2.pk},
                    {"hostId": host_3.pk, "componentId": component_1_s_2.pk},
                ],
            }

            response = self.client.v2[self.cluster_3, "actions", action.pk, "processes", process.id, "operation"].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {
                        "step_id": current_step_id,
                        "process_sync_key": process.sync_key,
                        "host_component_map_delta": host_component_map_delta,
                    },
                }
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

        with self.subTest(f"retrieve process for {self.cluster_3}"):
            response = self.client.v2[
                self.cluster_3,
                "actions",
                self.get_object_action_with_process(self.cluster_3).pk,
                "processes",
                process.id,
                "steps",
                current_step_id,
            ].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertDictEqual(
                response.json()["delta"],
                {
                    "add": [
                        {"hostId": host_1.pk, "componentId": component_1_s_1.pk},
                        {"hostId": host_2.pk, "componentId": component_1_s_2.pk},
                        {"hostId": host_3.pk, "componentId": component_1_s_2.pk},
                    ],
                    "remove": [],
                },
            )
            self.assertCountEqual(
                response.json()["cumulativeDelta"]["add"],
                [
                    {"hostId": host_1.pk, "componentId": component_1_s_1.pk},
                    {"hostId": host_2.pk, "componentId": component_1_s_2.pk},
                    {"hostId": host_3.pk, "componentId": component_1_s_2.pk},
                ],
            )
            self.assertCountEqual(response.json()["cumulativeDelta"]["remove"], [])

    def test_adcm_7298_submit_mapping_not_add_service_in_step_spec_success(self):
        self.create_services(["service_1"], cluster=self.cluster_3)
        component_1_s1 = Component.objects.get(
            prototype__name="component_1_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
        host_1 = self.create_host(provider=self.provider, name="host-1", cluster=self.cluster_3)

        action = self.get_object_action_with_process(self.cluster_3)
        process = self.start_process(self.cluster_3, action)
        cfg_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")
        target_mapping_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping", display_name="change mapping"
        )

        payload = {"config": {"integer_field": 200, "string_field": "str"}, "adcmMeta": {}}
        self.submit_config_step(
            target=self.cluster_3, action=action, process=process, step_id=cfg_step.id, config_payload=payload
        )

        process.refresh_from_db()

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(current_step_id, target_mapping_step.id)
        self.assertEqual(last_completed_step_id, cfg_step.id)

        inputs_count = ProcessStepInput.objects.filter(step_id=target_mapping_step.id).count()
        self.assertEqual(inputs_count, 0)

        process.refresh_from_db()

        hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_1_s1.pk}]}
        self.submit_step_r(
            target=self.cluster_3,
            action=action,
            process_id=process.id,
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "step_id": target_mapping_step.id,
                    "process_sync_key": process.sync_key,
                    "host_component_map_delta": hc_delta,
                },
            },
        )

        step_input = ProcessStepInput.objects.get(step_id=target_mapping_step.id)
        add_delta = {"add": [{"host_id": host_1.pk, "component_id": component_1_s1.pk}]}
        expected_input_mapping = {"delta": {"remove": [], **add_delta}, "cumulative_delta": {"remove": [], **add_delta}}
        self.assertDictEqual(step_input.mapping, expected_input_mapping)
        self.assertIsNone(step_input.configuration)
        self.assertIsNone(step_input.job)

        process.refresh_from_db()
        self.assertTrue(process.current_step.id > target_mapping_step.id)

    def test_adcm_7295_submit_mapping_payload_validation(self):
        self.create_services(["service_1"], cluster=self.cluster_3)
        component_1_s1 = Component.objects.get(
            prototype__name="component_1_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
        host_1 = self.create_host(provider=self.provider, name="host-1", cluster=self.cluster_3)

        action = self.get_object_action_with_process(self.cluster_3)
        process = self.start_process(self.cluster_3, action)
        cfg_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")
        target_mapping_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping", display_name="change mapping"
        )

        payload = {"config": {"integer_field": 200, "string_field": "str"}, "adcmMeta": {}}
        self.submit_config_step(
            target=self.cluster_3, action=action, process=process, step_id=cfg_step.id, config_payload=payload
        )

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(current_step_id, target_mapping_step.id)
        self.assertEqual(last_completed_step_id, cfg_step.id)

        inputs_count = ProcessStepInput.objects.filter(step_id=target_mapping_step.id).count()
        self.assertEqual(inputs_count, 0)

        process.refresh_from_db()
        hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_1_s1.pk}]}

        correct_payload = {
            "method": ProcessOperationType.SUBMIT,
            "params": {
                "stepId": target_mapping_step.id,
                "processSyncKey": process.sync_key,
                "hostComponentMapDelta": hc_delta,
            },
        }

        for param in ("stepId", "processSyncKey", "hostComponentMapDelta"):
            with self.subTest(f"{param} -> {param}New"):
                wrong_payload = deepcopy(correct_payload)
                wrong_payload["params"][f"{param}New"] = wrong_payload["params"].pop(param)

                self.submit_step_r(
                    target=self.cluster_3,
                    action=action,
                    process_id=process.id,
                    data=wrong_payload,
                    expected_status=HTTP_400_BAD_REQUEST,
                )

            with self.subTest(f"Missing `{param}`"):
                wrong_payload = deepcopy(correct_payload)
                del wrong_payload["params"][param]

                self.submit_step_r(
                    target=self.cluster_3,
                    action=action,
                    process_id=process.id,
                    data=wrong_payload,
                    expected_status=HTTP_400_BAD_REQUEST,
                )

    def test_adcm_7302_submit_mapping_step_restrictions_fail(self):
        self.create_services(["service_1", "service_2"], cluster=self.cluster_3)
        component_1_s1 = Component.objects.get(
            prototype__name="component_1_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
        component_free_s1 = Component.objects.get(
            prototype__name="free_component_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
        component_1_s2 = Component.objects.get(
            prototype__name="component_1_s2", service__prototype__name="service_2", cluster=self.cluster_3
        )
        host_1 = self.create_host(provider=self.provider, name="host-1", cluster=self.cluster_3)

        action = self.get_object_action_with_process(self.cluster_3)
        process = self.start_process(self.cluster_3, action)
        cfg_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")
        first_mapping_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping", display_name="change mapping"
        )

        payload = {"config": {"integer_field": 200, "string_field": "str"}, "adcmMeta": {}}
        self.submit_config_step(
            target=self.cluster_3, action=action, process=process, step_id=cfg_step.id, config_payload=payload
        )

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(current_step_id, first_mapping_step.id)
        self.assertEqual(last_completed_step_id, cfg_step.id)

        inputs_count = ProcessStepInput.objects.filter(step_id=first_mapping_step.id).count()
        self.assertEqual(inputs_count, 0)

        first_mapping_step.refresh_from_db()
        expected_step_spec = [
            {
                "service": component_1_s1.service.prototype.name,
                "component": component_1_s1.prototype.name,
                "operation": "add",
            },
            {
                "service": component_1_s2.service.prototype.name,
                "component": component_1_s2.prototype.name,
                "operation": "add",
            },
        ]
        self.assertListEqual(first_mapping_step.step_spec, expected_step_spec)

        def submit_mapping_step(hc_delta: dict, step_id: int, expected_status: int = HTTP_200_OK):
            process.refresh_from_db()
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": step_id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": hc_delta,
                },
            }
            return self.submit_step_r(
                target=self.cluster_3,
                action=action,
                process_id=process.id,
                data=payload,
                expected_status=expected_status,
            )

        with self.subTest("Submit `add not specified` payload"):
            hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_free_s1.pk}]}
            response = submit_mapping_step(hc_delta, first_mapping_step.id, expected_status=HTTP_409_CONFLICT)

            expected_response = {
                "code": "ACTION_PROCESS_OPERATION_CONFLICT",
                "level": "error",
                "desc": "Add operation is not allowed for "
                f'"{component_free_s1.service.prototype.name}.{component_free_s1.prototype.name}". '
                'Allowed components for add: "service_1.component_1_s1", "service_2.component_1_s2".',
            }
            self.assertDictEqual(response.json(), expected_response)

        with self.subTest("Submit `remove not specified` payload"):
            hc_delta = {"remove": [{"hostId": host_1.pk, "componentId": component_free_s1.pk}]}
            response = submit_mapping_step(hc_delta, first_mapping_step.id, expected_status=HTTP_409_CONFLICT)
            expected_response = {
                "code": "ACTION_PROCESS_OPERATION_CONFLICT",
                "level": "error",
                "desc": "Remove operation is not allowed for "
                f'"{component_free_s1.service.prototype.name}.{component_free_s1.prototype.name}". '
                "Allowed components for remove: none.",
            }
            self.assertDictEqual(response.json(), expected_response)

        with self.subTest("Submit `add already existing` payload"):
            hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_1_s2.pk}]}

            self.set_hostcomponent(cluster=self.cluster_3, entries=[(host_1, component_1_s2)])
            response = submit_mapping_step(hc_delta, first_mapping_step.id, expected_status=HTTP_409_CONFLICT)
            expected_response = {
                "code": "ACTION_PROCESS_OPERATION_CONFLICT",
                "level": "error",
                "desc": "Add operation is not allowed for "
                f'"{component_1_s2.service.prototype.name}.{component_1_s2.prototype.name}". Already mapped.',
            }
            self.assertDictEqual(response.json(), expected_response)

        self.clear_hostcomponent_mapping(cluster_id=self.cluster_3.id)
        response = submit_mapping_step(hc_delta, first_mapping_step.id)

        second_mapping_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping_again", display_name="change mapping again"
        )
        process.refresh_from_db()
        self.assertEqual(process.current_step_id, second_mapping_step.id)
        target_hc_rule = {
            "service": component_1_s1.service.prototype.name,
            "component": component_1_s1.prototype.name,
            "operation": "remove",
        }
        self.assertIn(target_hc_rule, second_mapping_step.step_spec)

        with self.subTest("Submit `remove absent` payload"):
            hc_delta = {"remove": [{"hostId": host_1.pk, "componentId": component_1_s1.pk}]}
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": second_mapping_step.id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": hc_delta,
                },
            }
            response = self.submit_step_r(
                target=self.cluster_3,
                action=action,
                process_id=process.id,
                data=payload,
                expected_status=HTTP_409_CONFLICT,
            )
            expected_response = {
                "code": "ACTION_PROCESS_OPERATION_CONFLICT",
                "level": "error",
                "desc": "Remove operation is not allowed for "
                f'"{component_1_s1.service.prototype.name}.{component_1_s1.prototype.name}". Not mapped.',
            }
            self.assertDictEqual(response.json(), expected_response)

    def test_adcm_7393_invalid_mapping_template_fail(self):
        bundle_dir = self.test_bundles_dir / "wizard_broken_hc_step"
        bundle = self.create_bundle(src=bundle_dir)
        cluster = self.create_cluster(bundle=bundle, name="cluster_with_broken_hc_step")

        action_first_step_fail = Action.objects.get(prototype=cluster.prototype, name="wizard_first_step_broken")
        action_second_step_fail = Action.objects.get(prototype=cluster.prototype, name="wizard_second_step_broken")

        # first step
        response = self.start_process_r(target=cluster, action=action_first_step_fail).json()
        process_id, current_step_id = response["id"], response["currentStep"]
        target_step = ProcessStep.objects.get(process_id=process_id, name="first_broken_mapping_step")

        self.assertEqual(target_step.id, current_step_id)
        self.assertEqual(target_step.state, ProcessStepState.BROKEN)

        # second step after submitting first
        response = self.start_process_r(target=cluster, action=action_second_step_fail).json()
        process_id, current_step_id = response["id"], response["currentStep"]
        config_step = ProcessStep.objects.get(id=current_step_id, process_id=process_id, name="first_config_step")
        target_step = ProcessStep.objects.get(process_id=process_id, name="second_broken_mapping_step")
        process = Process.objects.get(id=process_id)

        self.assertEqual(config_step.id, current_step_id)
        payload = {
            "method": "submit_step",
            "params": {
                "processSyncKey": process.sync_key,
                "stepId": config_step.id,
                "configuration": {"config": {"float": 0.3}, "adcmMeta": {}},
            },
        }
        response = self.submit_step_r(cluster, action_second_step_fail, process.pk, data=payload)
        config_step.refresh_from_db()
        self.assertEqual(config_step.state, ProcessStepState.COMPLETED)

        target_step.refresh_from_db()
        self.assertEqual(response.json()["currentStep"], target_step.pk)
        self.assertEqual(target_step.state, ProcessStepState.BROKEN)

    def _test_adcm_7308_submit_mapping_component_constraint(
        self,
        cluster,
        action: str,
        service: str,
        component: str,
        initial_hc: list[Host],
        hc: dict[Literal["add", "remove"], list[Host]],
    ):
        action = Action.objects.get(prototype=cluster.prototype, name=action)
        service = self.create_services([service], cluster=cluster)[0]
        component = Component.objects.get(prototype__name=component, service=service, cluster=cluster)

        # set initial hc mapping
        initial_hc = initial_hc or []
        response = self.client.v2[cluster, "mapping"].post(
            data=[{"hostId": host.pk, "componentId": component.pk} for host in initial_hc],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())

        # init process
        process = self.start_process(cluster, action)
        step = process.steps.get()

        # submit mapping step
        hc_delta = {
            op: [{"hostId": host.pk, "componentId": component.pk} for host in hosts] for op, hosts in hc.items()
        }
        payload = {
            "method": ProcessOperationType.SUBMIT,
            "params": {
                "stepId": step.id,
                "processSyncKey": process.sync_key,
                "hostComponentMapDelta": hc_delta,
            },
        }

        response = self.submit_step_r(
            cluster, action, process.pk, data=payload, expected_status=HTTP_409_CONFLICT
        ).json()
        self.assertEqual(response["code"], "COMPONENT_CONSTRAINT_ERROR")
        self.assertEqual(response["level"], "error")
        self.assertRegex(response["desc"], r'Component ".*" of service ".*" has unsatisfied constraint:')

        # cleanup
        self.cleanup_process_hc_service(cluster_id=cluster.id, service_ids=[service.id], process_id=process.id)

    def test_adcm_7308_submit_mapping_component_constraints_fail(self):
        cluster = self.cluster_with_mapping_restrictions
        host_1 = self.create_host(provider=self.provider, name="host-1", cluster=cluster)
        host_2 = self.create_host(provider=self.provider, name="host-2", cluster=cluster)
        host_3 = self.create_host(provider=self.provider, name="host-3", cluster=cluster)

        for action, service, component, initial_hc, hc in (
            ("action_c_one", "service_with_one_component_constraint", "one", [host_1], {"add": [host_2]}),
            ("action_c_one", "service_with_one_component_constraint", "one", [host_1], {"remove": [host_1]}),
            (
                "action_c_one_odd_first_variant",
                "service_with_one_odd_component_constraint_1",
                "one_odd_first_variant",
                [host_1],
                {"add": [host_2]},
            ),
            (
                "action_c_one_odd_first_variant",
                "service_with_one_odd_component_constraint_1",
                "one_odd_first_variant",
                [host_1],
                {"remove": [host_1]},
            ),
            (
                "action_c_one_odd_second_variant",
                "service_with_one_odd_component_constraint_2",
                "one_odd_second_variant",
                [host_1],
                {"add": [host_2]},
            ),
            (
                "action_c_one_odd_second_variant",
                "service_with_one_odd_component_constraint_2",
                "one_odd_second_variant",
                [host_1],
                {"remove": [host_1]},
            ),
            (
                "action_c_one_plus",
                "service_with_one_plus_component_constraint",
                "one_plus",
                [host_1, host_2],
                {"remove": [host_1, host_2]},
            ),
            (
                "action_c_one_two",
                "service_with_one_two_component_constraint",
                "one_two",
                [host_1],
                {"remove": [host_1]},
            ),
            (
                "action_c_one_two",
                "service_with_one_two_component_constraint",
                "one_two",
                [host_1],
                {"add": [host_2, host_3]},
            ),
            (
                "action_c_plus",
                "service_with_plus_component_constraint",
                "plus",
                [host_1, host_2, host_3],
                {"remove": [host_1]},
            ),
            (
                "action_c_zero_odd",
                "service_with_zero_odd_component_constraint",
                "zero_odd",
                [],
                {"add": [host_1, host_2]},
            ),
            (
                "action_c_zero_odd",
                "service_with_zero_odd_component_constraint",
                "zero_odd",
                [host_1],
                {"add": [host_3]},
            ),
            (
                "action_c_zero_odd",
                "service_with_zero_odd_component_constraint",
                "zero_odd",
                [host_1, host_2, host_3],
                {"remove": [host_2]},
            ),
            (
                "action_c_zero_one",
                "service_with_zero_one_component_constraint",
                "zero_one",
                [],
                {"add": [host_1, host_2]},
            ),
            (
                "action_c_zero_one",
                "service_with_zero_one_component_constraint",
                "zero_one",
                [host_1],
                {"add": [host_2]},
            ),
        ):
            # check delta component constraint violations on first step
            with self.subTest(f"{action=}, {service=}, {component=}, {initial_hc=}, {hc=}"):
                self._test_adcm_7308_submit_mapping_component_constraint(
                    cluster=cluster, action=action, service=service, component=component, initial_hc=initial_hc, hc=hc
                )

        # scenario: there is previous mapping step with correct cumulative_delta.
        # This delta must be considered in new step checks
        with self.subTest("Check delta constraint violations on second step"):
            action = Action.objects.get(prototype=cluster.prototype, name="action_two_mapping_steps")
            service = self.create_services(["service_with_zero_one_component_constraint"], cluster=cluster)[0]
            component = Component.objects.get(prototype__name="zero_one", service=service, cluster=cluster)

            # init process
            process = self.start_process(cluster, action.pk)
            step_id = process.current_step.id

            # submit first mapping step
            operations_endpoint = self.client.v2[cluster, "actions", action.id, "processes", process.id, "operation"]
            hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component.pk}]}
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": step_id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": hc_delta,
                },
            }
            response = operations_endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_200_OK)

            # submit second step violating (considering previous step's cumulative_delta) component constraint
            process.refresh_from_db()
            self.assertNotEqual(process.current_step_id, step_id)
            self.assertEqual(process.last_completed_step_id, step_id)

            hc_delta = {"add": [{"hostId": host_2.pk, "componentId": component.pk}]}
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": process.current_step_id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": hc_delta,
                },
            }
            response = operations_endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            response = response.json()
            self.assertEqual(response["code"], "COMPONENT_CONSTRAINT_ERROR")
            self.assertEqual(response["level"], "error")
            self.assertRegex(response["desc"], r'Component ".*" of service ".*" has unsatisfied constraint:')

    def test_adcm_7310_submit_mapping_with_mm_fail(self):
        cluster = self.cluster_with_mapping_restrictions
        service = self.create_services(["service_with_zero_one_component_constraint"], cluster=cluster)[0]
        component = Component.objects.get(prototype__name="zero_one", service=service, cluster=cluster)
        action = Action.objects.get(name="action_c_zero_one", prototype=cluster.prototype)
        host = self.create_host(provider=self.provider, name="host-1", cluster=cluster)

        # init process
        process = self.start_process(cluster, action.pk)

        with self.subTest("Host in mm"):
            response = self.client.v2[host, "maintenance-mode"].post(data={"maintenanceMode": "on"})
            self.assertEqual(response.status_code, HTTP_200_OK)

            operations_endpoint = self.client.v2[cluster, "actions", action.id, "processes", process.id, "operation"]
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": process.current_step_id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": {"add": [{"hostId": host.pk, "componentId": component.pk}]},
                },
            }
            response = operations_endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            expected_response = {
                "code": "INVALID_HC_HOST_IN_MM",
                "level": "error",
                "desc": "You can't save hc with hosts in maintenance mode",
            }
            self.assertDictEqual(response.json(), expected_response)

            response = self.client.v2[host, "maintenance-mode"].post(data={"maintenanceMode": "off"})
            self.assertEqual(response.status_code, HTTP_200_OK)

    def _7313_prepare_env_get_operation_endpoint_and_process(
        self, cluster, action_name: str
    ) -> tuple[APINode, Process]:
        action = Action.objects.get(name=action_name, prototype=cluster.prototype)
        process = self.start_process(cluster, action.pk)
        return self.client.v2[cluster, "actions", action.id, "processes", process.id, "operation"], process

    def test_7313_submit_mapping_step_dependencies_fail(self):
        cluster = self.cluster_with_mapping_restrictions
        host = self.create_host(provider=self.provider, name="host-1", cluster=cluster)

        with self.subTest("Service requires service"):
            endpoint, process = self._7313_prepare_env_get_operation_endpoint_and_process(
                cluster=cluster, action_name="action_service_requires_service"
            )
            service = self.create_services(["service_requires_service"], cluster=cluster)[0]
            component = Component.objects.get(prototype__name="component_1", service=service, cluster=cluster)

            # submit with unsatisfied requirement
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": process.current_step_id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": {"add": [{"hostId": host.pk, "componentId": component.pk}]},
                },
            }
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            expected_response = {
                "code": "SERVICE_CONFLICT",
                "level": "error",
                "desc": 'No required service "service_required" for service "service_requires_service"',
            }
            self.assertDictEqual(response.json(), expected_response)

            # satisfy requirements, try again
            required_service = self.create_services(["service_required"], cluster=cluster)[0]
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_200_OK)

            self.cleanup_process_hc_service(
                cluster_id=cluster.id, service_ids=[service.id, required_service.id], process_id=process.id
            )

        with self.subTest("Service requires component"):
            endpoint, process = self._7313_prepare_env_get_operation_endpoint_and_process(
                cluster=cluster, action_name="action_service_requires_component"
            )
            service = self.create_services(["service_requires_component"], cluster=cluster)[0]
            component = Component.objects.get(prototype__name="component_1", service=service, cluster=cluster)
            service_with_required_component = self.create_services(
                ["service_with_component_required"], cluster=cluster
            )[0]
            required_component = Component.objects.get(
                prototype__name="required_component", service=service_with_required_component, cluster=cluster
            )
            not_required_component = Component.objects.get(
                prototype__name="not_required_component", service=service_with_required_component, cluster=cluster
            )

            # submit with unsatisfied requirement
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": process.current_step_id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": {
                        "add": [
                            {"hostId": host.pk, "componentId": component.pk},
                            {"hostId": host.pk, "componentId": not_required_component.pk},
                        ]
                    },
                },
            }
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            expected_response = {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": 'No required component "required_component" of service "service_with_component_required" for '
                'service "service_requires_component"',
            }
            self.assertDictEqual(response.json(), expected_response)

            # satisfy requirements, try again
            payload["params"]["hostComponentMapDelta"]["add"] = [
                {"hostId": host.pk, "componentId": component.pk},
                {"hostId": host.pk, "componentId": required_component.pk},
            ]
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_200_OK)

            self.cleanup_process_hc_service(
                cluster_id=cluster.id,
                service_ids=[service.id, service_with_required_component.id],
                process_id=process.id,
            )

        with self.subTest("Service with bound component"):
            host_2 = self.create_host(provider=self.provider, name="host-2", cluster=cluster)

            endpoint, process = self._7313_prepare_env_get_operation_endpoint_and_process(
                cluster=cluster, action_name="action_bound_component"
            )
            service = self.create_services(["service_with_bound_component"], cluster=cluster)[0]
            component = Component.objects.get(prototype__name="bound_component", service=service, cluster=cluster)
            bound_target_service = self.create_services(["bound_target_service"], cluster=cluster)[0]
            bound_target_component = Component.objects.get(
                prototype__name="bound_target_component", service=bound_target_service, cluster=cluster
            )

            # submit with unsatisfied requirement
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": process.current_step_id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": {
                        "add": [
                            {"hostId": host.pk, "componentId": component.pk},
                            {"hostId": host_2.pk, "componentId": component.pk},
                            {"hostId": host.pk, "componentId": bound_target_component.pk},
                        ]
                    },
                },
            }
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            expected_response = {
                "code": "COMPONENT_CONSTRAINT_ERROR",
                "level": "error",
                "desc": 'Component `bound_to` restriction violated.\nEach host with component "bound_target_component" '
                'of service "bound_target_service" should have mapped component "bound_component" of service '
                '"service_with_bound_component".',
            }
            self.assertDictEqual(response.json(), expected_response)

            # satisfy requirements, try again
            payload["params"]["hostComponentMapDelta"]["add"].append(
                {"hostId": host_2.pk, "componentId": bound_target_component.pk}
            )
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_200_OK)

            self.cleanup_process_hc_service(
                cluster_id=cluster.id, service_ids=[service.id, bound_target_service.id], process_id=process.id
            )

    def test_adcm_7451_retrieve_second_mapping_step_success(self):
        self.create_services(["service_1", "service_2"], cluster=self.cluster_3)
        component_1_s1 = Component.objects.get(
            prototype__name="component_1_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
        component_1_s2 = Component.objects.get(
            prototype__name="component_1_s2", service__prototype__name="service_2", cluster=self.cluster_3
        )
        host_1 = self.create_host(provider=self.provider, name="host-1", cluster=self.cluster_3)
        action = self.get_object_action_with_process(self.cluster_3)
        process = self.start_process(self.cluster_3, action)

        # submit config step
        cfg_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")
        payload = {"config": {"integer_field": 200, "string_field": "str"}, "adcmMeta": {}}
        response = self.submit_config_step(
            target=self.cluster_3, action=action, process=process, step_id=cfg_step.id, config_payload=payload
        )

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        first_mapping_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping", display_name="change mapping"
        )
        self.assertEqual(current_step_id, first_mapping_step.id)
        self.assertEqual(last_completed_step_id, cfg_step.id)

        # submit first mapping step
        process.refresh_from_db()
        first_mapping_step_hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_1_s1.pk}]}
        payload = {
            "method": ProcessOperationType.SUBMIT,
            "params": {
                "stepId": first_mapping_step.id,
                "processSyncKey": process.sync_key,
                "hostComponentMapDelta": first_mapping_step_hc_delta,
            },
        }
        response = self.submit_step_r(target=self.cluster_3, action=action, process_id=process.id, data=payload)

        # retrieve second mapping step
        second_mapping_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping_again", display_name="change mapping again"
        )
        response = self.get_step_r(
            target=self.cluster_3, action=action, process_id=process.id, step_id=second_mapping_step.id
        )
        response = response.json()
        self.assertIsNone(response["delta"])
        expected_cumulative_delta = {"remove": [], **first_mapping_step_hc_delta}
        self.assertDictEqual(response["cumulativeDelta"], expected_cumulative_delta)

        # submit second mapping step
        process.refresh_from_db()
        second_mapping_step_hc_delta = {
            "add": [{"hostId": host_1.pk, "componentId": component_1_s2.pk}],
            "remove": [{"hostId": host_1.pk, "componentId": component_1_s1.pk}],
        }
        payload = {
            "method": ProcessOperationType.SUBMIT,
            "params": {
                "stepId": second_mapping_step.id,
                "processSyncKey": process.sync_key,
                "hostComponentMapDelta": second_mapping_step_hc_delta,
            },
        }
        self.submit_step_r(target=self.cluster_3, action=action, process_id=process.id, data=payload)

        # retrieve second mapping step again
        response = self.get_step_r(
            target=self.cluster_3, action=action, process_id=process.id, step_id=second_mapping_step.id
        )

        response = response.json()
        self.assertDictEqual(response["delta"], second_mapping_step_hc_delta)
        expected_cumulative_delta = {"add": second_mapping_step_hc_delta["add"], "remove": []}
        self.assertDictEqual(response["cumulativeDelta"], expected_cumulative_delta)
