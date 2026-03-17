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

from adcm.tests.base import BusinessLogicMixin
from cm.converters import orm_object_to_core_type
from cm.legacy.services.action_process.schema_validation import ProcessOperationType
from cm.legacy.services.action_process.types import ProcessState, ProcessStepState
from cm.models import (
    ADCM,
    Action,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    ConcernType,
    Process,
    ProcessStep,
)
from django.contrib.contenttypes.models import ContentType
from infra.services import get_config_service
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from api_v2.tests.base import APIV2Mixin
from api_v2.tests.setup.base import BaseAPITestCase
from api_v2.tests.test_wizard.helpers import WizardProcessHelpers, render_template


class TestWizardActionProcessExecution(BaseAPITestCase, APIV2Mixin, WizardProcessHelpers, BusinessLogicMixin):
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

        provider_bundle_path = self.test_bundles_dir / "provider"
        self.provider_bundle = self.create_bundle(src=provider_bundle_path)
        self.provider = self.create_provider(
            bundle=self.provider_bundle,
            name=f"provider_{suffix}",
            description=f"provider_{suffix}",
        )

        broken_render_process_bundle = self.test_bundles_dir / "broken_render_action_process"
        self.broken_process_bundle = self.create_bundle(src=broken_render_process_bundle)
        self.cluster_broken_process = self.create_cluster(
            bundle=self.broken_process_bundle,
            name=f"broken_process_{suffix}",
        )
        self.action_broken_process = Action.objects.get(
            prototype=self.cluster_broken_process.prototype, name="broken_process"
        )
        self.action_broken_configuration_step = Action.objects.get(
            prototype=self.cluster_broken_process.prototype, name="broken_configuration_step"
        )
        self.action_broken_operation_step = Action.objects.get(
            prototype=self.cluster_broken_process.prototype, name="broken_operation_step"
        )

    def test_create_process_success(self):
        expected_response_template = self.test_files_dir / "responses" / "wizard_process" / "create_process.yml"

        for obj in (self.cluster_1, self.service_1, self.component_1):
            with self.subTest(f"create process for {obj}"):
                response = self.start_process_r(obj, self.get_object_action_with_process(obj).pk)

                response_data = response.json()

                self.assertEqual(
                    Process.objects.filter(target_id=obj.pk, target_type=orm_object_to_core_type(obj).value).count(),
                    1,
                )

                process = Process.objects.get(id=response_data["id"])

                self.assertEqual(ProcessStep.objects.filter(process=process).count(), 6)

                _step_ids = {f"{name}_id": id_ for name, id_ in process.steps.values_list("name", "id")}
                expected_response = render_template(
                    file=expected_response_template,
                    context={
                        "process_id": process.id,
                        "created_at": process.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                        **_step_ids,
                    },
                )

                self.assertDictContainsSubset(expected_response, response_data)

                flags = ConcernItem.objects.filter(
                    owner_id=self.cluster_1.pk,
                    owner_type=ContentType.objects.get_for_model(model=Cluster),
                    cause=ConcernCause.CONFIGURING_PROCESS,
                )
                self.assertEqual(flags.count(), 1)

                first_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1")
                self.assertIsNotNone(first_step.step_spec)
                self.assertEqual(first_step.state, ProcessStepState.CREATED)

                rest_steps_qs = ProcessStep.objects.filter(process_id=process.id, id__ne=first_step.id)
                self.assertSetEqual(set(rest_steps_qs.values_list("step_spec", flat=True)), {None})
                self.assertSetEqual(set(rest_steps_qs.values_list("state", flat=True)), {ProcessStepState.CREATED})

    def test_retrieve_action_with_process_success(self):
        with self.subTest("action without process"):
            response = self.client.v2[
                "adcm", "actions", Action.objects.filter(prototype=ADCM.objects.first().prototype).first().pk
            ].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIsNone(response.json()["processes"], None)

        for obj in (self.cluster_1, self.service_1, self.component_1):
            with self.subTest(f"action with process of {obj} without processes"):
                response = self.client.v2[obj, "actions", self.get_object_action_with_process(obj).pk].get()
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertListEqual(response.json()["processes"], [])

        for obj in (self.cluster_1, self.service_1, self.component_1):
            with self.subTest(f"action with process  of {obj} with process"):
                action = self.get_object_action_with_process(obj)
                process = self.start_process(obj, action)

                self.set_completed_fill_specs_create_inputs_for_steps_by_name(
                    process.id, {"stage1_step1", "stage2_step1"}
                )

                response = self.client.v2[obj, "actions", self.get_object_action_with_process(obj).pk].get()
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(len(response.json()["processes"]), 1)
                self.assertEqual(response.json()["processes"][0]["syncKey"], str(process.sync_key))

    def test_wizard_action_run_with_object_concern_success(self):
        self.add_issue_and_concern_to_object(object_=self.cluster_1, cause=ConcernCause.CONFIG)

        action = self.get_object_action_with_process(self.cluster_1)
        response = self.start_process_r(target=self.cluster_1, action=action, expected_status=HTTP_409_CONFLICT)

        self.assertIn(f"object {self.cluster_1} has issues", response.json()["desc"])

    def test_complete_process_success(self):
        action = self.get_object_action_with_process(self.cluster_1)
        process = self.start_process(self.cluster_1, action)
        step_names = ProcessStep.objects.filter(process_id=process.id).values_list("name", flat=True)
        self.set_completed_fill_specs_create_inputs_for_steps_by_name(process_id=process.id, step_names=step_names)
        self.assertEqual(process.state, ProcessState.CREATED)

        payload = {"method": "complete", "params": {"processSyncKey": process.sync_key}}
        self.submit_step_r(target=self.cluster_1, action=action, process_id=process.id, data=payload)
        process.refresh_from_db()
        self.assertEqual(process.state, ProcessState.COMPLETED)

        flags = ConcernItem.objects.filter(
            owner_id=self.cluster_1.pk,
            owner_type=ContentType.objects.get_for_model(model=Cluster),
            cause=ConcernCause.CONFIGURING_PROCESS,
        )
        self.assertEqual(flags.count(), 0)

    def test_adcm_7150_second_step_broken(self):
        owner = self.cluster_broken_process
        action = Action.objects.get(name="broken_second_step")
        process = self.start_process(owner, action)
        correct_step, broken_step = tuple(ProcessStep.objects.filter(process_id=process.pk).order_by("id"))

        self.submit_config_step(
            owner,
            action,
            process,
            step_id=correct_step.pk,
            config_payload={"config": {"string": "value"}, "adcmMeta": {}},
        )

        correct_step.refresh_from_db()
        self.assertEqual(correct_step.state, ProcessStepState.COMPLETED)
        broken_step.refresh_from_db()
        self.assertEqual(broken_step.state, ProcessStepState.BROKEN)

    def test_adcm_7150_error_running_process_action_without_process(self):
        owner = self.cluster_1
        action = self.process_action_of_cluster

        response = self.client.v2[owner, "actions", action, "run"].post()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertIn("Process must be specified", response.json()["desc"])

    def test_adcm_7150_error_running_process_action_with_non_existent_process(self):
        owner = self.cluster_1
        action = self.process_action_of_cluster

        response = self.client.v2[owner, "actions", action, "run"].post(data={"process": {"id": 4}})

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND, response.json())
        self.assertIn("Process with id", response.json()["desc"])
        self.assertIn("not exist", response.json()["desc"])

    def test_adcm_7150_error_running_process_action_with_incomplete_process(self):
        owner = self.cluster_1
        action = self.process_action_of_cluster
        process = self.start_process_r(owner, action).json()

        response = self.client.v2[owner, "actions", action, "run"].post(data={"process": {"id": process["id"]}})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response.json())
        self.assertIn("completed state", response.json()["desc"])

    def test_create_process_with_broken_render_fail(self):
        response = self.client.v2[
            self.cluster_broken_process, "actions", self.action_broken_process.id, "processes"
        ].post(data={})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertIn("Extra inputs are not permitted", response.json()["desc"])

    def test_render_broken_configuration_step_success(self):
        # step is expected to be broken
        response = self.start_process_r(self.cluster_broken_process, self.action_broken_configuration_step.pk)
        first_step = response.json()["stages"][0]["steps"][0]

        self.assertEqual(first_step["state"], "broken")

    def test_render_broken_operation_step_success(self):
        # step is expected to be broken
        response = self.start_process_r(
            self.cluster_broken_process,
            self.action_broken_operation_step.pk,
        )
        first_step = response.json()["stages"][0]["steps"][0]

        self.assertEqual(first_step["state"], "broken")

    def test_adcm_7151_task_display_name_success(self):
        action = Action.objects.get(name="wizard_operation_as_first", prototype=self.cluster_1.prototype)
        process = self.start_process(self.cluster_1, action)
        expected_display_name = f"{action.display_name} (find me In here)"
        self.submit_step(
            owner=self.cluster_1,
            action=action,
            process_id=process.pk,
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "processSyncKey": process.sync_key,
                    "stepId": process.current_step.pk,
                },
            },
        )

        launched_task = self.task_runner.expect_task_launched()

        response = (self.client.v2 / "tasks" / launched_task.id).get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["displayName"], expected_display_name)

        # get tasks list
        response = (self.client.v2 / "tasks").get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        response = response.json()["results"]

        task_with_step_response = [task for task in response if task["id"] == launched_task.id][0]
        self.assertEqual(task_with_step_response["displayName"], expected_display_name)

    def test_adcm_process_action_errors(self):
        # action does not exist
        action_id = 9999999
        expected_response = {"code": "API_ERROR", "desc": f"Can't retrieve action #{action_id}", "level": "ERROR"}

        response = (self.client.v2[self.cluster_1] / "actions" / action_id / "processes").post(data={})

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertDictEqual(response.json(), expected_response)

        # wrong prototype
        service_action = Action.objects.get(name="wizard_service_action", prototype=self.service_1.prototype)
        expected_response = {
            "code": "API_ERROR",
            "desc": f"Prototypes mismatch for {service_action} and {self.cluster_1}",
            "level": "ERROR",
        }

        response = self.start_process_r(
            target=self.cluster_1, action=service_action, expected_status=HTTP_404_NOT_FOUND
        )

        self.assertDictEqual(response.json(), expected_response)

        # regular action on host
        host = self.create_host(provider=self.provider, name="test-host", cluster=self.cluster_1)
        expected_response = {
            "code": "API_ERROR",
            "desc": f"{service_action} is not a host_action",
            "level": "ERROR",
        }

        response = self.start_process_r(target=host, action=service_action, expected_status=HTTP_404_NOT_FOUND)

        self.assertDictEqual(response.json(), expected_response)

        # host_action on not mapped host
        service_host_action = Action.objects.get(
            name="wizard_host_action_from_service", prototype=self.service_1.prototype
        )
        expected_response = {
            "code": "API_ERROR",
            "desc": f"Prototypes mismatch for {service_host_action} and {host}",
            "level": "ERROR",
        }

        response = self.start_process_r(target=host, action=service_host_action, expected_status=HTTP_404_NOT_FOUND)

        self.assertDictEqual(response.json(), expected_response)

        # map it, try again
        component = Component.objects.get(service=self.service_1, prototype__name="component_1")
        self.set_hostcomponent(self.cluster_1, entries=((host, component),))

        self.start_process_r(target=host, action=service_host_action)

        # action is disallowed
        cluster_action = Action.objects.get(name="wizard_cluster_action", prototype=self.cluster_1.prototype)
        cluster_action.state_unavailable = "any"
        cluster_action.save(update_fields=["state_unavailable"])
        expected_response = {
            "code": "API_ERROR",
            "desc": f"{cluster_action} is not allowed for {self.cluster_1}",
            "level": "ERROR",
        }

        response = self.start_process_r(
            target=self.cluster_1, action=cluster_action, expected_status=HTTP_404_NOT_FOUND
        )

        self.assertDictEqual(response.json(), expected_response)

    def test_adcm_7551_7841_process_on_host_action(self):
        expected_step_spec = {
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
                {"service": self.service_1.name, "component": self.component_1.name, "operation": "remove"}
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

        cluster, service, component = self.cluster_1, self.service_1, self.component_1
        host = self.create_host(provider=self.provider, name="test-host", cluster=cluster)

        self.set_hostcomponent(cluster=cluster, entries=((host, component),))
        host_action_from_cluster = Action.objects.get(
            name="wizard_host_action_from_cluster", prototype=cluster.prototype
        )
        host_action_from_service = Action.objects.get(
            name="wizard_host_action_from_service", prototype=service.prototype
        )
        host_action_from_component = Action.objects.get(
            name="wizard_host_action_from_component", prototype=component.prototype
        )

        host_actions = (
            (host_action_from_cluster, cluster),
            (host_action_from_service, service),
            (host_action_from_component, component),
        )

        for action, owner in host_actions:
            with self.subTest(f"Retrieve {action=}"):
                response = self.client.v2[cluster, "hosts", host, "actions", action].get()
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertListEqual(response.json()["processes"], [])

            with self.subTest(f"Process on {action=}"):
                host_concerns = ConcernItem.objects.filter(
                    owner_id=host.id,
                    owner_type=ContentType.objects.get_for_model(host),
                    cause=ConcernCause.CONFIGURING_PROCESS,
                )
                self.assertEqual(host_concerns.count(), 0)

                action_endpoint = self.client.v2[cluster, "hosts", host, "actions", action]

                process = self.start_process(owner=host, action=action)
                self.assertEqual(process.state, ProcessState.CREATED.value)

                host_concerns = ConcernItem.objects.filter(
                    owner_id=host.id,
                    owner_type=ContentType.objects.get_for_model(host),
                    cause=ConcernCause.CONFIGURING_PROCESS,
                )
                self.assertEqual(host_concerns.count(), 1)
                concern = host_concerns.get()
                self.assertEqual(concern.type, ConcernType.FLAG)
                self.assertEqual(concern.name, "action_process_running")

                # first config step
                step_1_config = ProcessStep.objects.get(process=process, name="step_1_config")
                self.assertEqual(step_1_config.state, ProcessStepState.CREATED.value)
                self.assertListEqual(step_1_config.step_spec, expected_step_spec[step_1_config.name])

                # retrieve step from host_action via owner, not target (host)
                expected_response = {
                    "code": "API_ERROR",
                    "desc": f"Wrong target {owner} for a host action {action}",
                    "level": "ERROR",
                }
                response = self.client.v2[
                    owner, "actions", action.id, "processes", process.id, "steps", step_1_config.id
                ].get()
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
                self.assertEqual(response.json(), expected_response)

                # correct retrieve step
                self.get_step_r(
                    target=host,
                    action=action,
                    process_id=process.id,
                    step_id=step_1_config.id,
                    expected_status=HTTP_200_OK,
                )

                submit_payload = {
                    "method": ProcessOperationType.SUBMIT,
                    "params": {
                        "processSyncKey": process.sync_key,
                        "stepId": step_1_config.pk,
                        "configuration": {
                            "config": {
                                "float": 0.4,
                                "step_variant_from_config": "entry1",
                            },
                            "adcmMeta": {},
                        },
                    },
                }

                # submit step from host_action via owner, not target (host)
                expected_response = {
                    "code": "API_ERROR",
                    "desc": f"Wrong target {owner} for a host action {action}",
                    "level": "ERROR",
                }
                response = self.client.v2[owner, "actions", action.id, "processes", process.id, "operation"].post(
                    data=submit_payload
                )
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
                self.assertEqual(response.json(), expected_response)

                # submit with wrong variant choice (not in owner's config)
                wrong_variant_payload = deepcopy(submit_payload)
                wrong_variant_payload["params"]["configuration"]["config"]["step_variant_from_config"] = "abc"
                self.submit_step_r(
                    target=host,
                    action=action,
                    process_id=process.pk,
                    data=wrong_variant_payload,
                    expected_status=HTTP_409_CONFLICT,
                )

                # correct submit
                self.submit_step_r(target=host, action=action, process_id=process.pk, data=submit_payload)

                step_1_config.refresh_from_db()
                self.assertEqual(step_1_config.state, ProcessStepState.COMPLETED)

                # second mapping step
                process.refresh_from_db()
                step_2_mapping = ProcessStep.objects.get(process=process, name="step_2_mapping")
                self.assertListEqual(step_2_mapping.step_spec, expected_step_spec[step_2_mapping.name])
                self.assertEqual(step_2_mapping.state, ProcessStepState.CREATED.value)

                self.submit_step_r(
                    target=host,
                    action=action,
                    process_id=process.pk,
                    data={
                        "method": ProcessOperationType.SUBMIT,
                        "params": {
                            "processSyncKey": process.sync_key,
                            "stepId": step_2_mapping.id,
                            "hostComponentMapDelta": {"remove": [{"hostId": host.id, "componentId": component.id}]},
                        },
                    },
                )

                step_2_mapping.refresh_from_db()
                self.assertEqual(step_2_mapping.state, ProcessStepState.COMPLETED)

                # third operation step
                process.refresh_from_db()
                step_3_operation = ProcessStep.objects.get(process=process, name="step_3_operation")
                self.assertListEqual(step_3_operation.step_spec, expected_step_spec[step_3_operation.name])
                self.assertEqual(step_3_operation.state, ProcessStepState.CREATED.value)

                self.submit_step_r(
                    target=host,
                    action=action,
                    process_id=process.pk,
                    data={
                        "method": ProcessOperationType.SUBMIT,
                        "params": {"processSyncKey": process.sync_key, "stepId": step_3_operation.pk},
                    },
                )

                launched_task = self.task_runner.expect_task_launched()
                self.task_runner.run_task(launched_task.id)

                step_3_operation.refresh_from_db()
                self.assertEqual(step_3_operation.state, ProcessStepState.COMPLETED)

                # complete process
                host_concerns = ConcernItem.objects.filter(
                    owner_id=host.id,
                    owner_type=ContentType.objects.get_for_model(host),
                    cause=ConcernCause.CONFIGURING_PROCESS,
                )
                self.assertEqual(host_concerns.count(), 1)

                process.refresh_from_db()
                self.submit_step_r(
                    target=host,
                    action=action,
                    process_id=process.pk,
                    data={
                        "method": ProcessOperationType.COMPLETE,
                        "params": {"processSyncKey": process.sync_key},
                    },
                )

                process.refresh_from_db()
                self.assertEqual(process.state, ProcessState.COMPLETED.value)

                host_concerns = ConcernItem.objects.filter(
                    owner_id=host.id,
                    owner_type=ContentType.objects.get_for_model(host),
                    cause=ConcernCause.CONFIGURING_PROCESS,
                )
                self.assertEqual(host_concerns.count(), 0)

                # run process action
                response = (action_endpoint / "run").post(data={"process": {"id": process.id}})
                self.assertEqual(response.status_code, HTTP_200_OK)

                launched_task = self.task_runner.expect_task_launched(response.json()["id"])

                # remove job lock
                self.delete_concern_by_name(object_=host, name="job_lock")
