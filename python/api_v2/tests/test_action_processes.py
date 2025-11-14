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
from pathlib import Path
from typing import Any, Collection
from uuid import uuid4
import json
import unittest

from cm.converters import orm_object_to_core_descriptor, orm_object_to_core_type
from cm.issue import add_concern_to_object
from cm.models import (
    ADCM,
    Action,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    HostComponent,
    Process,
    ProcessStep,
    ProcessStepInput,
    Service,
    TaskLog,
)
from cm.services.action_process.operations import (
    find_current_and_last_completed_steps,
)
from cm.services.action_process.render_step import RenderStepContext, fill_step_spec
from cm.services.action_process.schema_validation import ProcessOperationType
from cm.services.action_process.types import ProcessState, ProcessStepState
from cm.services.bundle_alt.render import TaskArgs
from cm.services.bundle_alt.render._context import prepare_context_for_task
from cm.services.cluster import retrieve_cluster_topology
from cm.services.concern import create_issue
from cm.services.job.action import ActionRunPayload, run_action
from cm.services.job.run._target_factories import (
    internal_script_hc_apply,
    prepare_ansible_environment,
    prepare_ansible_inventory,
)
from cm.services.job.run.repo import JobRepoImpl
from cm.tests.mocks.task_runner import RunTaskMock
from core.job.runners import ADCMSettings, AnsibleSettings, ConsulSettings, ExternalSettings, IntegrationsSettings
from core.job.types import AssociatedProcess
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from jinja2 import Template
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
import yaml

from api_v2.tests.base import BaseAPITestCase


def render_template(file: Path, context: dict) -> Any:
    data = Template(source=file.read_text(encoding="utf-8")).render(**context)
    return yaml.safe_load(data)


class TestActionProcess(BaseAPITestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle = self.test_bundles_dir / "wizard_action"
        cluster_bundle_hc_apply = self.test_bundles_dir / "wizard_hc_apply_bad_definition"
        cluster_bundle_mapping = self.test_bundles_dir / "wizard_mapping"
        self.bundle_1 = self.add_bundle(source_dir=cluster_bundle)
        self.bundle_2 = self.add_bundle(source_dir=cluster_bundle_hc_apply)
        self.bundle_3 = self.add_bundle(source_dir=cluster_bundle_mapping)
        self.cluster_1 = self.add_cluster(bundle=self.bundle_1, name="cluster_1", description="cluster_1")
        self.cluster_2 = self.add_cluster(bundle=self.bundle_2, name="cluster_2", description="cluster_2")
        self.cluster_3 = self.add_cluster(bundle=self.bundle_3, name="cluster_3", description="cluster_3")
        self.process_action_of_cluster = self.get_object_action_with_process(self.cluster_1)
        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster_1).first()
        self.component_1 = Component.objects.filter(service=self.service_1).first()

        provider_bundle_path = self.test_bundles_dir / "provider"
        self.provider_bundle = self.add_bundle(source_dir=provider_bundle_path)
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider", description="provider")

        config_bundle = self.test_bundles_dir / "wizard_config"
        self.config_bundle = self.add_bundle(source_dir=config_bundle)
        self.config_cluster = self.add_cluster(bundle=self.config_bundle, name="config_cluster")

        broken_render_process_bundle = self.test_bundles_dir / "broken_render_action_process"
        self.broken_process_bundle = self.add_bundle(source_dir=broken_render_process_bundle)
        self.cluster_broken_process = self.add_cluster(bundle=self.broken_process_bundle, name="broken_process")
        self.action_broken_process = Action.objects.get(
            prototype=self.cluster_broken_process.prototype, name="broken_process"
        )
        self.action_broken_configuration_step = Action.objects.get(
            prototype=self.cluster_broken_process.prototype, name="broken_configuration_step"
        )
        self.action_broken_operation_step = Action.objects.get(
            prototype=self.cluster_broken_process.prototype, name="broken_operation_step"
        )

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.wizard_action_conf = ExternalSettings(
            adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
            ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
            consul=ConsulSettings(
                url=settings.CONSUL_URL,
                datacenter=settings.CONSUL_DATACENTER,
                client_key_file=settings.CONSUL_CLIENT_KEY_FILE,
                client_cacert_file=settings.CONSUL_CACERT_FILE,
                client_cert_file=settings.CONSUL_CLIENT_KEY_FILE,
            ),
        )

    def initiate_process(self, owner, action, expected_status: int = HTTP_201_CREATED):
        response = self.client.v2[owner, "actions", action, "processes"].post(data={})
        self.assertEqual(response.status_code, expected_status, response.json())
        return response

    def submit_config_step(self, obj: Cluster, process: Process, step_id: int, config_payload: dict) -> Response:
        process.refresh_from_db()
        endpoint = self.get_endpoint_to_processes(obj=obj) / process / "operation"
        payload = {
            "method": "submit_step",
            "params": {"processSyncKey": process.sync_key, "stepId": step_id, "configuration": config_payload},
        }

        return endpoint.post(data=payload)

    def make_step_current(self, step: ProcessStep) -> None:
        steps_qs = ProcessStep.objects.filter(process_id=step.process_id)
        steps_qs.filter(id__lt=step.id).update(state=ProcessStepState.COMPLETED)

        self_and_next_ids = set(steps_qs.filter(id__gte=step.id).values_list("id", flat=True))
        steps_qs.filter(id__in=self_and_next_ids).update(state=ProcessStepState.CREATED)
        ProcessStepInput.objects.filter(step_id__in=self_and_next_ids).delete()

    def start_process(self, obj: Cluster | Service | Component):
        endpoint = self.get_endpoint_to_processes(obj)
        response = endpoint.post(data={})
        return response.json()["id"]

    def get_endpoint_to_processes(self, obj: Cluster | Service | Component):
        return self.client.v2[obj, "actions", self.get_object_action_with_process(obj).pk, "processes"]

    def get_process(self, process_id: int) -> Process:
        return Process.objects.get(pk=process_id)

    def get_object_action_with_process(self, obj: Cluster | Service | Component) -> Action:
        return Action.objects.get(name="wizard_jinja", prototype=obj.prototype)

    @staticmethod
    def set_completed_fill_specs_create_inputs_for_steps_by_name(process_id: int, step_names: Collection[str]) -> None:
        # Fill previous steps' `step_spec`, create inputs for them, set `completed` state
        for step in ProcessStep.objects.filter(process_id=process_id, name__in=step_names):
            step.step_spec = [{"name": "a", "subname": ""}]
            step.state = ProcessStepState.COMPLETED
            step.save(update_fields=["step_spec", "state"])
            ProcessStepInput.objects.create(step_id=step.id, job=None, configuration={"config": {}, "attr": {}})

    def test_create_process_success(self):
        self.assertEqual(Process.objects.count(), 0)
        self.assertEqual(ProcessStep.objects.count(), 0)

        self.client.login(**self.test_user_credentials)

        with self.subTest("No view permissions"):
            response = self.client.v2[
                self.cluster_1, "actions", self.get_object_action_with_process(self.cluster_1).pk, "processes"
            ].post(data={})
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("No run permissions"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
                response = self.client.v2[
                    self.cluster_1, "actions", self.get_object_action_with_process(self.cluster_1).pk, "processes"
                ].post(data={})
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.client.login(username="admin", password="admin")

        with self.subTest("All permissions"):
            for obj in (self.cluster_1, self.service_1, self.component_1):
                with self.subTest(f"create process for {obj}"):
                    response = self.client.v2[
                        obj, "actions", self.get_object_action_with_process(obj).pk, "processes"
                    ].post(data={})

                    self.assertEqual(response.status_code, HTTP_201_CREATED)
                    self.assertEqual(
                        Process.objects.filter(
                            object_id=obj.pk, object_type=orm_object_to_core_type(obj).value
                        ).count(),
                        1,
                    )

                    process = Process.objects.get(object_id=obj.pk, object_type=orm_object_to_core_type(obj).value)

                    flags = ConcernItem.objects.filter(
                        owner_id=self.cluster_1.pk,
                        owner_type=ContentType.objects.get_for_model(model=Cluster),
                        cause=ConcernCause.CONFIGURING_PROCESS,
                    )
                    self.assertEqual(flags.count(), 1)

                    self.assertEqual(ProcessStep.objects.filter(process=process).count(), 6)

                    expected_response_template = (
                        self.test_files_dir / "responses" / "action_process" / "create_process.yml"
                    )
                    _step_ids = {f"{name}_id": id_ for name, id_ in process.steps.values_list("name", "id")}
                    expected_response = render_template(
                        file=expected_response_template,
                        context={
                            "process_id": process.id,
                            "created_at": process.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                            **_step_ids,
                        },
                    )

                    response = response.json()

                    self.assertDictContainsSubset(expected_response, response)

                    first_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1")
                    self.assertIsNotNone(first_step.step_spec)
                    self.assertEqual(first_step.state, ProcessStepState.CREATED)

                    rest_steps_qs = ProcessStep.objects.filter(process_id=process.id, id__ne=first_step.id)
                    self.assertSetEqual(set(rest_steps_qs.values_list("step_spec", flat=True)), {None})
                    self.assertSetEqual(set(rest_steps_qs.values_list("state", flat=True)), {ProcessStepState.CREATED})

    def test_retrieve_config_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        target_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")

        self.client.login(**self.test_user_credentials)

        with self.subTest("No view permissions"):
            response = self.client.v2[
                self.cluster_1,
                "actions",
                self.get_object_action_with_process(self.cluster_1).pk,
                "processes",
                process.id,
                "steps",
                target_step.pk,
            ].get()
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("No run permissions"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
                response = self.client.v2[
                    self.cluster_1,
                    "actions",
                    self.get_object_action_with_process(self.cluster_1).pk,
                    "processes",
                    process.id,
                    "steps",
                    target_step.pk,
                ].get()
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.client.login(username="admin", password="admin")

        with self.subTest("All permissions"):
            for obj in (self.cluster_1, self.service_1, self.component_1):
                with self.subTest(f"retrieve process for {obj}"):
                    response = self.client.v2[
                        obj,
                        "actions",
                        self.get_object_action_with_process(obj).pk,
                        "processes",
                        process.id,
                        "steps",
                        target_step.pk,
                    ].get()
                    self.assertEqual(response.status_code, HTTP_200_OK)

                    expected_response = {
                        "name": "stage1_step1",
                        "displayName": "Stage1.Step1",
                        "id": target_step.id,
                        "type": "configuration",
                        "state": "created",
                        "configuration": {
                            "configSchema": {
                                "$schema": "https://json-schema.org/draft/2020-12/schema",
                                "title": "Configuration",
                                "description": "",
                                "readOnly": False,
                                "adcmMeta": {
                                    "isAdvanced": False,
                                    "isInvisible": False,
                                    "activation": None,
                                    "synchronization": None,
                                    "nullValue": None,
                                    "isSecret": False,
                                    "stringExtra": None,
                                    "enumExtra": None,
                                },
                                "type": "object",
                                "properties": {
                                    "integer_field": {
                                        "title": "integer_field",
                                        "type": "integer",
                                        "description": "",
                                        "default": 2,
                                        "readOnly": False,
                                        "adcmMeta": {
                                            "isAdvanced": False,
                                            "isInvisible": False,
                                            "activation": None,
                                            "synchronization": None,
                                            "isSecret": False,
                                            "stringExtra": None,
                                            "enumExtra": None,
                                        },
                                    },
                                    "string_field": {
                                        "title": "string_field",
                                        "type": "string",
                                        "description": "",
                                        "default": "string_value",
                                        "readOnly": False,
                                        "adcmMeta": {
                                            "isAdvanced": False,
                                            "isInvisible": False,
                                            "activation": None,
                                            "synchronization": None,
                                            "isSecret": False,
                                            "stringExtra": {"isMultiline": False},
                                            "enumExtra": None,
                                        },
                                        "minLength": 1,
                                    },
                                },
                                "additionalProperties": False,
                                "required": ["integer_field", "string_field"],
                            },
                            "adcmMeta": {},
                            "config": {"integer_field": 2, "string_field": "string_value"},
                        },
                    }
                    self.assertDictEqual(response.json(), expected_response)

                    target_step.refresh_from_db()
                    expected_spec = [
                        {
                            "name": "integer_field",
                            "type": "integer",
                            "limits": {},
                            "default": 2,
                            "subname": "",
                            "required": True,
                            "ui_options": {},
                            "description": "",
                            "display_name": "integer_field",
                            "ansible_options": {"unsafe": False},
                            "group_customization": False,
                        },
                        {
                            "name": "string_field",
                            "type": "string",
                            "limits": {},
                            "default": "string_value",
                            "subname": "",
                            "required": True,
                            "ui_options": {},
                            "description": "",
                            "display_name": "string_field",
                            "ansible_options": {"unsafe": False},
                            "group_customization": False,
                        },
                    ]
                    self.assertListEqual(target_step.step_spec, expected_spec)

                    response_template = (
                        self.test_files_dir / "responses" / "action_process" / "retrieve_config_step.yml"
                    )
                    expected_response = render_template(file=response_template, context={"step_id": target_step.id})
                    self.assertDictEqual(response.json(), expected_response)

    @unittest.skip("ADCM-7359 Too custom data preparation, need patch / test case update")
    def test_retrieve_operation_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        target_step = ProcessStep.objects.get(process_id=process.id, name="stage2_step2", display_name="Stage2.Step2")

        previous_step_names = {"stage1_step1", "stage2_step1"}
        self.set_completed_fill_specs_create_inputs_for_steps_by_name(
            process_id=process.id, step_names=previous_step_names
        )

        self.client.login(**self.test_user_credentials)

        with self.subTest("No view permissions"):
            response = self.client.v2[
                self.cluster_1,
                "actions",
                self.get_object_action_with_process(self.cluster_1).pk,
                "processes",
                process.id,
                "steps",
                target_step.pk,
            ].get()
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("No run permissions"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
                response = self.client.v2[
                    self.cluster_1,
                    "actions",
                    self.get_object_action_with_process(self.cluster_1).pk,
                    "processes",
                    process.id,
                    "steps",
                    target_step.pk,
                ].get()
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.client.login(username="admin", password="admin")

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(target_step.id, current_step_id)
        self.assertEqual(current_step_id - 1, last_completed_step_id)

        new_state = "new_state"
        self.cluster_1.state = new_state
        self.cluster_1.save(update_fields=["state"])
        fill_step_spec(
            step_id=current_step_id,
            context=RenderStepContext(
                process_id=process.id,
                action_id=self.process_action_of_cluster.id,
                object=orm_object_to_core_descriptor(self.cluster_1),
            ),
        )

        with self.subTest("All permissions"):
            for obj in (self.cluster_1, self.service_1, self.component_1):
                with self.subTest(f"retrieve operation for {obj}"):
                    response = self.client.v2[
                        obj,
                        "actions",
                        self.get_object_action_with_process(obj).pk,
                        "processes",
                        process.id,
                        "steps",
                        target_step.pk,
                    ].get()
                    self.assertEqual(response.status_code, HTTP_200_OK)

                    expected_response = {
                        "name": "stage2_step2",
                        "displayName": "Stage2.Step2",
                        "id": target_step.id,
                        "state": "created",
                        "task": None,
                        "type": "operation",
                        "uiOptions": {"buttonName": "ButtonName"},
                    }
                    self.assertDictEqual(response.json(), expected_response)

                    target_step.refresh_from_db()
                    expected_spec = [
                        {
                            "name": "sleep_script",
                            "params": {"test_params": [new_state]},
                            "script": "wizard_jinja/scripts/sleep.yaml",
                            "script_type": "ansible",
                            "display_name": "Sleep",
                            "state_on_fail": "",
                            "allow_to_terminate": False,
                            "multi_state_on_fail_set": [],
                            "multi_state_on_fail_unset": [],
                        }
                    ]
                    self.assertListEqual(target_step.step_spec, expected_spec)

                    response_template = (
                        self.test_files_dir / "responses" / "action_process" / "retrieve_operation_step.yml"
                    )
                    expected_response = render_template(file=response_template, context={"step_id": target_step.id})
                    self.assertDictEqual(response.json(), expected_response)

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
                process = self.get_process(self.start_process(obj))

                self.set_completed_fill_specs_create_inputs_for_steps_by_name(
                    process.id, {"stage1_step1", "stage2_step1"}
                )

                response = self.client.v2[obj, "actions", self.get_object_action_with_process(obj).pk].get()
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(len(response.json()["processes"]), 1)
                self.assertEqual(response.json()["processes"][0]["syncKey"], str(process.sync_key))

    @unittest.skip("ADCM-7359 Too custom data preparation, need patch / test case update")
    def test_submit_operation_hc_apply_fail(self):
        process = self.get_process(self.start_process(self.cluster_2))
        previous_step_names = {"stage1_step1"}

        target_operation_step = ProcessStep.objects.get(process_id=process.id, name="hc_apply", display_name="hc apply")

        self.set_completed_fill_specs_create_inputs_for_steps_by_name(process.id, previous_step_names)

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(current_step_id, target_operation_step.id)

        fill_step_spec(
            step_id=current_step_id,
            context=RenderStepContext(
                process_id=process.id,
                action_id=self.process_action_of_cluster.pk,
                object=orm_object_to_core_descriptor(self.cluster_1),
            ),
        )
        target_operation_step.refresh_from_db()
        self.assertEqual(target_operation_step.state, ProcessStepState.BROKEN.value)

    @unittest.skip("ADCM-7359 Too custom data preparation, need patch / test case update")
    def test_submit_operation_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        initial_sync_key = process.sync_key
        previous_step_names = {"stage1_step1", "stage2_step1"}

        target_operation_step = ProcessStep.objects.get(
            process_id=process.id, name="stage2_step2", display_name="Stage2.Step2"
        )

        self.set_completed_fill_specs_create_inputs_for_steps_by_name(process.id, previous_step_names)
        self.client.login(**self.test_user_credentials)

        with self.subTest("No view permissions"):
            # submit step
            response = self.client.v2[
                self.cluster_1, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {"step_id": target_operation_step.id, "process_sync_key": process.sync_key},
                }
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("No run permissions"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
                # submit step
                response = self.client.v2[
                    self.cluster_1, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
                ].post(
                    data={
                        "method": ProcessOperationType.SUBMIT,
                        "params": {"step_id": target_operation_step.id, "process_sync_key": process.sync_key},
                    }
                )
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("All permissions"):
            self.client.login(username="admin", password="admin")

            # render step
            current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
                steps=ProcessStep.objects.filter(process_id=process.id)
            )
            self.assertEqual(current_step_id, target_operation_step.id)
            fill_step_spec(
                step_id=current_step_id,
                context=RenderStepContext(
                    process_id=process.id,
                    action_id=self.process_action_of_cluster.pk,
                    object=orm_object_to_core_descriptor(self.cluster_1),
                ),
            )

            self.assertFalse(ProcessStepInput.objects.filter(step_id=target_operation_step.id).exists())
            self.assertFalse(TaskLog.objects.filter(action=self.process_action_of_cluster).exists())

            # submit step
            response = self.client.v2[
                self.cluster_1, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {"step_id": target_operation_step.id, "process_sync_key": process.sync_key},
                }
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["id"], process.id)
            self.assertEqual(response.json()["createdAt"], str(process.created_at.isoformat().replace("+00:00", "Z")))
            self.assertEqual(sum(len(stage["steps"]) for stage in response.json()["stages"]), process.steps.count())

            target_operation_step.refresh_from_db()
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
            self.assertListEqual(target_operation_step.step_spec, expected_spec)

            task = TaskLog.objects.get(action=self.process_action_of_cluster)
            input_ = ProcessStepInput.objects.get(step_id=target_operation_step.id)

            self.assertIsNone(input_.configuration)
            self.assertEqual(input_.job_id, task.id)

            process.refresh_from_db()
            self.assertNotEqual(initial_sync_key, process.sync_key)

            # check that previous steps and inputs are not affected
            for step in ProcessStep.objects.filter(process_id=process.id, name__in=previous_step_names):
                # taken hardcoded values from "fill" function, which is bad from test design perspective
                self.assertListEqual(step.step_spec, [{"name": "a", "subname": ""}])
                input_ = ProcessStepInput.objects.get(step_id=step.id)
                self.assertDictEqual(input_.configuration, {"config": {}, "attr": {}})
                self.assertIsNone(input_.job)

    @unittest.skip("ADCM-7359 Too custom data preparation, need patch / test case update")
    def test_submit_mapping_success(self):
        self.add_services_to_cluster(["service_1", "service_2", "service_3"], cluster=self.cluster_3)
        component_1_s_1 = Component.objects.filter(service__prototype__name="service_1", cluster=self.cluster_3).first()
        component_1_s_2 = Component.objects.filter(service__prototype__name="service_2", cluster=self.cluster_3).first()
        component_1_s_3 = Component.objects.filter(service__prototype__name="service_3", cluster=self.cluster_3).first()
        host_1 = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_3)
        host_2 = self.add_host(provider=self.provider, fqdn="host-2", cluster=self.cluster_3)
        host_3 = self.add_host(provider=self.provider, fqdn="host-3", cluster=self.cluster_3)

        process = self.get_process(self.start_process(self.cluster_3))
        previous_step_names = {"stage1_step1"}

        target_operation_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping", display_name="change mapping"
        )

        self.set_completed_fill_specs_create_inputs_for_steps_by_name(process.id, previous_step_names)

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(current_step_id, target_operation_step.id)

        # rendering
        fill_step_spec(
            step_id=current_step_id,
            context=RenderStepContext(
                process_id=process.id,
                action_id=self.process_action_of_cluster.pk,
                object=orm_object_to_core_descriptor(self.cluster_3),
            ),
        )
        with self.subTest("Submit mapping not component in step spec (fail)"):
            host_component_map_delta = {
                "add": [
                    {"hostId": host_1.pk, "componentId": component_1_s_3.pk},
                ],
            }

            response = self.client.v2[
                self.cluster_3, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {
                        "step_id": target_operation_step.id,
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

            response = self.client.v2[
                self.cluster_3, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {
                        "step_id": target_operation_step.id,
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

            response = self.client.v2[
                self.cluster_3, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {
                        "step_id": target_operation_step.id,
                        "process_sync_key": process.sync_key,
                        "host_component_map_delta": host_component_map_delta,
                    },
                }
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            process.refresh_from_db()

            host_component_map_delta = {
                "add": [
                    {"hostId": host_2.pk, "componentId": component_1_s_1.pk},
                ],
                "remove": [
                    {"hostId": host_1.pk, "componentId": component_1_s_1.pk},
                ],
            }

            target_operation_step = ProcessStep.objects.get(
                process_id=process.id, name="stage1_mapping_again", display_name="change mapping again"
            )

            response = self.client.v2[
                self.cluster_3, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {
                        "step_id": target_operation_step.id,
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
                target_operation_step.pk,
            ].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertDictEqual(
                response.json()["delta"],
                {
                    "add": [{"componentId": component_1_s_1.pk, "hostId": host_2.pk}],
                    "remove": [{"componentId": component_1_s_1.pk, "hostId": host_1.pk}],
                },
            )
            self.assertCountEqual(
                response.json()["cumulativeDelta"]["add"],
                [
                    {"componentId": component_1_s_1.pk, "hostId": host_2.pk},
                    {"componentId": component_1_s_2.pk, "hostId": host_2.pk},
                    {"componentId": component_1_s_2.pk, "hostId": host_3.pk},
                ],
            )
            self.assertCountEqual(response.json()["cumulativeDelta"]["remove"], [])

    @unittest.skip("ADCM-7359 Too custom data preparation, need patch / test case update")
    def test_mapping_groups_success(self):
        self.add_services_to_cluster(["service_1", "service_2"], cluster=self.cluster_3)
        component_1_s_1 = Component.objects.filter(service__prototype__name="service_1", cluster=self.cluster_3).first()
        component_1_s_2 = Component.objects.filter(service__prototype__name="service_2", cluster=self.cluster_3).first()
        host_1 = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_3)
        host_2 = self.add_host(provider=self.provider, fqdn="host-2", cluster=self.cluster_3)
        host_3 = self.add_host(provider=self.provider, fqdn="host-3", cluster=self.cluster_3)

        process = self.get_process(self.start_process(self.cluster_3))
        previous_step_names = {"stage1_step1"}

        target_operation_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping", display_name="change mapping"
        )

        self.set_completed_fill_specs_create_inputs_for_steps_by_name(process.id, previous_step_names)

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(current_step_id, target_operation_step.id)

        # rendering
        fill_step_spec(
            step_id=current_step_id,
            context=RenderStepContext(
                process_id=process.id,
                action_id=self.process_action_of_cluster.pk,
                object=orm_object_to_core_descriptor(self.cluster_3),
            ),
        )

        host_component_map_delta = {
            "add": [
                {"hostId": host_1.pk, "componentId": component_1_s_1.pk},
                {"hostId": host_2.pk, "componentId": component_1_s_2.pk},
                {"hostId": host_3.pk, "componentId": component_1_s_2.pk},
            ],
        }

        response = self.client.v2[
            self.cluster_3, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
        ].post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "step_id": target_operation_step.id,
                    "process_sync_key": process.sync_key,
                    "host_component_map_delta": host_component_map_delta,
                },
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        process.refresh_from_db()

        host_component_map_delta = {
            "add": [
                {"hostId": host_2.pk, "componentId": component_1_s_1.pk},
            ],
            "remove": [
                {"hostId": host_1.pk, "componentId": component_1_s_1.pk},
            ],
        }

        target_operation_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping_again", display_name="change mapping again"
        )

        response = self.client.v2[
            self.cluster_3, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
        ].post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "step_id": target_operation_step.id,
                    "process_sync_key": process.sync_key,
                    "host_component_map_delta": host_component_map_delta,
                },
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        with self.subTest("Check process context for action"):
            process.refresh_from_db()
            process.state = ProcessState.COMPLETED
            process.save()

            action = self.get_object_action_with_process(self.cluster_3)

            with RunTaskMock() as run_task:
                run_action(
                    action=action,
                    obj=self.cluster_3,
                    payload=ActionRunPayload(process=AssociatedProcess(id=process.pk)),
                )

            task = JobRepoImpl.get_task(run_task.target_task.id)
            job, *_ = JobRepoImpl.get_task_jobs(task_id=task.id)

            job_dir: Path = self.directories["RUN_DIR"] / str(job.id)
            job_dir.mkdir(parents=True)
            prepare_ansible_environment(task=task, job=job, configuration=self.wizard_action_conf)

            config_json = json.loads((job_dir / "config.json").read_text(encoding="utf-8"))

            stage1_mapping = config_json["process"]["stages"]["mapping"]["stage1_mapping"]["groups"]
            stage1_mapping_again = config_json["process"]["stages"]["mapping_again"]["stage1_mapping_again"]["groups"]

            task_context = prepare_context_for_task(
                TaskArgs(
                    target_object=self.cluster_3,
                    action=self.process_action_of_cluster,
                    config={},
                    verbose=False,
                    delta=None,
                    action_process=process,
                )
            )

            self.assertDictEqual(
                stage1_mapping,
                {"service_1.component_1.add": ["host-1"], "service_2.component_1.add": ["host-2", "host-3"]},
            )
            self.assertDictEqual(
                stage1_mapping_again,
                {"service_1.component_1.add": ["host-2"], "service_1.component_1.remove": ["host-1"]},
            )

            stage1_mapping = task_context["action"]["process"]["stages"]["mapping"]["stage1_mapping"]["groups"]
            stage1_mapping_again = task_context["action"]["process"]["stages"]["mapping_again"]["stage1_mapping_again"][
                "groups"
            ]

            self.assertDictEqual(
                stage1_mapping,
                {"service_1.component_1.add": ["host-1"], "service_2.component_1.add": ["host-2", "host-3"]},
            )
            self.assertDictEqual(
                stage1_mapping_again,
                {"service_1.component_1.add": ["host-2"], "service_1.component_1.remove": ["host-1"]},
            )
            self.assertDictEqual(
                task_context["groups"],
                {
                    "CLUSTER": ["host-1", "host-2", "host-3"],
                    "service_1.component_1.add": ["host-2"],
                    "service_2.component_1.add": ["host-2", "host-3"],
                },
            )

        with self.subTest("Check mapping after hc_apply run"):
            internal_script_hc_apply(task=task, job=job)

            actual_hc = set(
                HostComponent.objects.filter(cluster_id=self.cluster_3.pk).values_list("host_id", "component_id")
            )
            expected_hc = {
                (host_2.pk, component_1_s_1.pk),
                (host_2.pk, component_1_s_2.pk),
                (host_3.pk, component_1_s_2.pk),
            }
            self.assertSetEqual(actual_hc, expected_hc)

        with self.subTest("Check generated inventory for cumulative delta"):
            inventory = prepare_ansible_inventory(
                task=JobRepoImpl.get_task(run_task.target_task.id),
                topology=retrieve_cluster_topology(self.cluster_3.pk),
            )
            self.assertDictEqual(
                inventory["all"]["children"],
                {
                    "CLUSTER": {"hosts": {"host-1": {}, "host-2": {}, "host-3": {}}},
                    "service_1": {"hosts": {"host-2": {}}},
                    "service_1.component_1": {"hosts": {"host-2": {}}},
                    "service_1.component_1.add": {"hosts": {"host-2": {}}},
                    "service_2": {"hosts": {"host-2": {}, "host-3": {}}},
                    "service_2.component_1": {"hosts": {"host-2": {}, "host-3": {}}},
                    "service_2.component_1.add": {"hosts": {"host-2": {}, "host-3": {}}},
                },
            )

    def test_wizard_action_run_with_object_concern_success(self):
        issue = create_issue(
            owner=CoreObjectDescriptor(id=self.cluster_1.id, type=ADCMCoreType.CLUSTER), cause=ConcernCause.CONFIG
        )
        add_concern_to_object(object_=self.cluster_1, concern=issue)

        endpoint = self.get_endpoint_to_processes(self.cluster_1)
        response = endpoint.post(data={})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertIn(f"object {self.cluster_1} has issues", response.json()["desc"])

    @unittest.skip("ADCM-7359 Too custom data preparation, need patch / test case update")
    def test_submit_config_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))

        first_step_id = (
            ProcessStep.objects.filter(process_id=process.id).values_list("id", flat=True).order_by("id").first()
        )
        self.assertEqual(process.current_step_id, first_step_id)
        self.assertIsNone(process.last_completed_step)

        process_sync_key_initial = process.sync_key
        target_config_step = ProcessStep.objects.get(
            process_id=process.id, name="stage2_step1", display_name="Stage2.Step1"
        )
        self.assertEqual(target_config_step.state, ProcessStepState.CREATED)

        test_step_spec = {"config": {}, "attr": {}}
        previous_step_names = {"stage1_step1"}
        self.set_completed_fill_specs_create_inputs_for_steps_by_name(
            process_id=process.id, step_names=previous_step_names
        )

        # render step
        current_step_id, _ = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(current_step_id, target_config_step.id)
        fill_step_spec(
            step_id=current_step_id,
            context=RenderStepContext(
                process_id=process.id,
                action_id=self.process_action_of_cluster.pk,
                object=orm_object_to_core_descriptor(self.cluster_1),
            ),
        )

        wrong_config = {"config": {"new": "config"}, "adcm_meta": {}}
        new_config = {"config": {"int": 22}, "adcm_meta": {}}

        for config, expected_code in ((wrong_config, HTTP_400_BAD_REQUEST), (new_config, HTTP_200_OK)):
            with self.subTest(f"Submit {config=}, {expected_code=}"):
                response = self.client.v2[
                    self.cluster_1, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
                ].post(
                    data={
                        "method": ProcessOperationType.SUBMIT,
                        "params": {
                            "configuration": config,
                            "step_id": target_config_step.id,
                            "process_sync_key": process.sync_key,
                        },
                    }
                )
                self.assertEqual(response.status_code, expected_code)

        # check that next steps' spec is rendered, no input; rest next steps are without specs and inputs
        expected_current_step_spec = [
            {
                "name": "int",
                "type": "integer",
                "limits": {},
                "default": 1,
                "subname": "",
                "required": True,
                "ui_options": {},
                "description": "",
                "display_name": "int",
                "ansible_options": {"unsafe": False},
                "group_customization": False,
            }
        ]
        expected_next_step_spec = [
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
        steps_qs = ProcessStep.objects.filter(process_id=process.id)
        expected_step_specs: dict[tuple, list[dict] | None] = {
            ("stage1_step1", "Stage1.Step1"): [{"name": "a", "subname": ""}],
            ("stage2_step1", "Stage2.Step1"): expected_current_step_spec,
            ("stage2_step2", "Stage2.Step2"): expected_next_step_spec,
            ("stage3_step1", "Stage3.Step1"): None,
            ("stage4_step1", "Stage4.Step1"): None,
            ("stage4_step2", "Stage4.Step2"): None,
        }
        actual_step_specs = {
            (name, display_name): spec
            for name, display_name, spec in steps_qs.values_list("name", "display_name", "step_spec")
        }
        self.assertDictEqual(actual_step_specs, expected_step_specs)

        expected_steps_with_inputs: set[int] = set(
            steps_qs.filter(name__in={"stage1_step1", "stage2_step1"}).values_list("id", flat=True)
        )
        actual_steps_with_inputs = set(
            ProcessStepInput.objects.filter(step_id__in=steps_qs.values_list("id", flat=True)).values_list(
                "step_id", flat=True
            )
        )
        self.assertSetEqual(expected_steps_with_inputs, actual_steps_with_inputs)

        # check inputs' config and job
        input_config = {"attr": new_config.pop("adcm_meta"), **new_config}
        for input_ in ProcessStepInput.objects.filter(step_id__in=steps_qs.values_list("id", flat=True)):
            expected_config = input_config if input_.step_id == target_config_step.id else test_step_spec
            self.assertDictEqual(input_.configuration, expected_config)
            self.assertIsNone(input_.job)

        # check that process's sync_key is updated
        process.refresh_from_db()
        self.assertNotEqual(process_sync_key_initial, process.sync_key)
        self.assertEqual(process.last_completed_step_id, target_config_step.id)

        target_config_step.refresh_from_db()
        self.assertEqual(target_config_step.state, ProcessStepState.COMPLETED)

    # disabled due to configs refactoring
    #
    #    def test_submit_step_config_called_success(self):
    #        process = self.get_process(self.start_process(self.cluster_1))
    #        process_sync_key = str(process.sync_key)
    #        step_id = process.steps.first().pk
    #        config = {"config": {"a": "b", "c": {}}, "adcmMeta": {"/a": {"isActive": True}}}
    #        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process / "operation"
    #
    #        self.assertEqual(process.state, ProcessState.CREATED)
    #
    #        with patch("api_v2.generic.action.process.views.perform_operation") as perform_operation_mock:
    #            payload = {
    #                "method": "submit_step",
    #                "params": {"processSyncKey": process_sync_key, "stepId": step_id, "configuration": config},
    #            }
    #            response = endpoint.post(data=payload)
    #            self.assertEqual(response.status_code, HTTP_200_OK)
    #
    #        expected_payload = SubmitStepPayload.model_validate(
    #            {
    #                "method": "submit_step",
    #                "params": {
    #                    "process_sync_key": process_sync_key,
    #                    "step_id": step_id,
    #                    "configuration": {"config": {"a": "b", "c": {}}, "adcm_meta": {"/a": {"isActive": True}}},
    #                },
    #            }
    #        )
    #        expected_context = OperationContext(
    #            object=orm_object_to_core_descriptor(self.cluster_1),
    #            action=ActionRepoImpl.get_action(id=self.process_action_of_cluster.id),
    #            config_processor=process_payload_config,
    #        )
    #        perform_operation_mock.assert_called_once_with(
    #            process_id=process.id, payload=expected_payload, context=expected_context
    #        )
    #
    #    def test_submit_step_job_called_success(self):
    #        process = self.get_process(self.start_process(self.cluster_1))
    #        process_sync_key = str(process.sync_key)
    #        step_id = process.steps.get(name="stage2_step2").pk
    #        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process / "operation"
    #
    #        self.assertEqual(process.state, ProcessState.CREATED)
    #
    #        # make all previous steps 'completed'
    #        ProcessStep.objects.filter(id__lt=step_id).update(state=ProcessStepState.COMPLETED)
    #
    #        with patch("api_v2.generic.action.process.views.perform_operation") as perform_operation_mock:
    #            payload = {
    #                "method": "submit_step",
    #                "params": {"processSyncKey": process_sync_key, "stepId": step_id},
    #            }
    #            response = endpoint.post(data=payload)
    #            self.assertEqual(response.status_code, HTTP_200_OK)
    #
    #        expected_payload = SubmitStepPayload.model_validate(
    #            {**payload, "params": {"process_sync_key": process_sync_key, "step_id": step_id}}
    #        )
    #        expected_context = OperationContext(
    #            object=orm_object_to_core_descriptor(self.cluster_1),
    #            action=ActionRepoImpl.get_action(id=self.process_action_of_cluster.id),
    #            config_processor=process_payload_config,
    #        )
    #        perform_operation_mock.assert_called_once_with(
    #            process_id=process.id, payload=expected_payload, context=expected_context
    #        )

    @unittest.skip("ADCM-7359 Too custom data preparation, need patch / test case update")
    def test_reset_operation_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        target_step_to_reset = ProcessStep.objects.get(process_id=process.id, name="stage3_step1")

        previous_step_names = list(
            ProcessStep.objects.filter(process_id=process.id, id__lt=target_step_to_reset.id).values_list(
                "name", flat=True
            )
        )
        current_step_name = [target_step_to_reset.name]
        next_step_names = list(
            ProcessStep.objects.filter(process_id=process.id, id__gt=target_step_to_reset.id).values_list(
                "name", flat=True
            )
        )

        test_spec = [{"name": "a", "subname": ""}]
        self.set_completed_fill_specs_create_inputs_for_steps_by_name(
            process.id, previous_step_names + current_step_name
        )
        # fill next steps spec to check it will be set to None
        ProcessStep.objects.filter(process_id=process.id, name__in=next_step_names).update(step_spec=test_spec)

        response = self.client.v2[
            self.cluster_1, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
        ].post(
            data={
                "method": ProcessOperationType.RESET,
                "params": {"step_id": target_step_to_reset.id, "process_sync_key": process.sync_key},
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        previous_step_ids = ProcessStep.objects.filter(process_id=process.id, name__in=previous_step_names).values_list(
            "id", flat=True
        )
        next_step_ids = ProcessStep.objects.filter(process_id=process.id, name__in=next_step_names).values_list(
            "id", flat=True
        )
        previous_qs = ProcessStep.objects.filter(process_id=process.id, id__in=previous_step_ids)
        current = ProcessStep.objects.get(process_id=process.id, id=target_step_to_reset.id)
        next_qs = ProcessStep.objects.filter(process_id=process.id, id__in=next_step_ids)

        # expecting:
        #   previous steps:
        #     - inputs exists
        #     - spec without changes
        #     - `completed` state
        #   current step (which we just resetted):
        #     - no input
        #     - freshly rendered spec
        #     - `created` state
        #   next steps:
        #     - no inputs
        #     - specs is None
        #     - `created` state

        actual_previous_inputs_count = ProcessStepInput.objects.filter(step_id__in=previous_step_ids).count()
        self.assertEqual(actual_previous_inputs_count, previous_qs.count())
        actual_previous_specs = list(previous_qs.values_list("step_spec", flat=True))
        self.assertListEqual(actual_previous_specs, [test_spec] * previous_qs.count())
        actual_previous_states = set(previous_qs.values_list("state", flat=True))
        self.assertSetEqual(actual_previous_states, {ProcessStepState.COMPLETED})

        actual_current_inputs_count = ProcessStepInput.objects.filter(step_id=current.id).count()
        self.assertEqual(actual_current_inputs_count, 0)
        expected_current_spec = [
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
        self.assertListEqual(current.step_spec, expected_current_spec)
        self.assertEqual(current.state, ProcessStepState.CREATED)

        actual_next_inputs_count = ProcessStepInput.objects.filter(step_id__in=next_step_ids).count()
        self.assertEqual(actual_next_inputs_count, 0)
        actual_next_steps_spec = set(next_qs.values_list("step_spec", flat=True))
        self.assertSetEqual(actual_next_steps_spec, {None})
        actual_next_states = set(next_qs.values_list("state", flat=True))
        self.assertSetEqual(actual_next_states, {ProcessStepState.CREATED})

    def test_complete_process_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        step_names = ProcessStep.objects.filter(process_id=process.id).values_list("name", flat=True)
        self.set_completed_fill_specs_create_inputs_for_steps_by_name(process_id=process.id, step_names=step_names)

        process_sync_key = process.sync_key
        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process / "operation"

        self.assertEqual(process.state, ProcessState.CREATED)

        payload = {"method": "complete", "params": {"processSyncKey": process_sync_key}}
        response = endpoint.post(data=payload)
        self.assertEqual(response.status_code, HTTP_200_OK)
        process.refresh_from_db()
        self.assertEqual(process.state, ProcessState.COMPLETED)

        flags = ConcernItem.objects.filter(
            owner_id=self.cluster_1.pk,
            owner_type=ContentType.objects.get_for_model(model=Cluster),
            cause=ConcernCause.CONFIGURING_PROCESS,
        )
        self.assertEqual(flags.count(), 0)

    def test_retrieve_process_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        self.assertEqual(process.state, ProcessState.CREATED)

        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process
        with self.subTest("All permissions"):
            response = endpoint.get()
            self.assertEqual(response.status_code, HTTP_200_OK)

        with self.subTest("No view permissions"):
            self.client.login(**self.test_user_credentials)
            response = endpoint.get()
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("No run permissions"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
                response = endpoint.get()
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_operation_validation_fail(self):
        process = self.get_process(self.start_process(self.cluster_1))
        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process / "operation"

        with self.subTest("Incorrect method"):
            payload = {"method": "notexist", "params": {"process_sync_key": process.sync_key}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            error = response.json()["desc"]
            self.assertIn(
                "Input tag 'notexist' found using 'method' does not match any of the expected tags",
                error,
            )

        with self.subTest("Incorrect payload for complete"):
            payload = {"method": "complete", "params": {}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            error = response.json()["desc"]
            self.assertIn("params.process_sync_key", error)
            self.assertIn("Field required [type=missing, input_value={}, input_type=dict]", error)

        with self.subTest("Incorrect payload for submit: missing stepId"):
            payload = {"method": "submit_step", "params": {"processSyncKey": process.sync_key}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            error = response.json()["desc"]
            # TODO: not informative error msg
            self.assertIn("5 validation errors for OperationPayloadSchema\npayload.submit_step.params.", error)

        with self.subTest("Incorrect payload for complete: wrong sync key"):
            wrong_sync_key = uuid4()
            payload = {"method": "complete", "params": {"processSyncKey": wrong_sync_key}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            error = response.json()["desc"]
            self.assertIn(f"Can't find Process #{process.pk} ({str(wrong_sync_key)})", error)

        with self.subTest("Incorrect payload for complete: wrong sync key type"):
            payload = {"method": "complete", "params": {"processSyncKey": "abs"}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            error = response.json()["desc"]
            self.assertIn("Input should be a valid UUID", error)

    def test_validation_submit_config(self):
        process = self.get_process(process_id=self.start_process(obj=self.config_cluster))
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
            response = self.submit_config_step(
                obj=self.config_cluster, process=process, step_id=step.id, config_payload=base_payload
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

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

        # fixme ADCM-7359 Make it expecting fail
        # with self.subTest("Correct wihtout not required field"):
        #    self.make_step_current(step=step)
        #    payload = deepcopy(base_payload)
        #    del payload["config"]["json_not_required"]

        #    response = self.submit_config_step(
        #        obj=self.config_cluster, process=process, step_id=step.id, config_payload=payload
        #    )
        #    self.assertEqual(response.status_code, HTTP_200_OK)

        #    # check absence of not required field in input
        #    input_ = ProcessStepInput.objects.get(step_id=step.id)
        #    expected_input = {
        #        "config": {
        #            "integer_field": 100,
        #            "agroup": {
        #                "str_in_agroup": "new str in agroup value",
        #                "json_in_agroup": {"new": "json", "in": "agroup"},
        #            },
        #        },
        #        "attr": {"agroup": {"active": True}},
        #    }
        #    self.assertDictEqual(input_.configuration, expected_input)

        with self.subTest("Without adcmMeta"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            del payload["adcmMeta"]

            response = self.submit_config_step(
                obj=self.config_cluster, process=process, step_id=step.id, config_payload=payload
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            # fixme ADCM-7359
            # expected_response = {
            #    "code": "ATTRIBUTE_ERROR",
            #    "desc": "there isn't `agroup` group in the `attr`",
            #    "level": "error",
            # }
            # self.assertDictEqual(response.json(), expected_response)

        with self.subTest("With empty adcmMeta"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            payload["adcmMeta"] = {}

            response = self.submit_config_step(
                obj=self.config_cluster, process=process, step_id=step.id, config_payload=payload
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            # fixme ADCM-7359
            # expected_response = {
            #    "code": "ATTRIBUTE_ERROR",
            #    "desc": "there isn't `agroup` group in the `attr`",
            #    "level": "error",
            # }
            # self.assertDictEqual(response.json(), expected_response)

        with self.subTest("With empty /agroup meta"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            payload["adcmMeta"]["/agroup"] = {}

            response = self.submit_config_step(
                obj=self.config_cluster, process=process, step_id=step.id, config_payload=payload
            )
            # todo ADCM-7359 check why here 400 (comare to previous message)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

            # fixme ADCM-7359
            # expected_response = {
            #    "code": "ATTRIBUTE_ERROR",
            #    "desc": 'there isn\'t `/agroup` group in the config (cluster "wizard_config" 1.0)',
            #    "level": "error",
            # }
            # self.assertDictEqual(response.json(), expected_response)

        with self.subTest("Without required field"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            del payload["config"]["integer_field"]

            response = self.submit_config_step(
                obj=self.config_cluster, process=process, step_id=step.id, config_payload=payload
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            # fixme ADCM-7359
            # expected_json_response = {
            #    "code": "CONFIG_KEY_ERROR",
            #    "desc": 'There is no required key "integer_field" in input config (cluster "wizard_config" 1.0)',
            #    "level": "error",
            # }
            # self.assertDictEqual(response.json(), expected_json_response)

    def test_retrieve_not_exist_process_fail(self):
        process = self.get_process(self.start_process(self.cluster_1))

        response = self.client.v2[
            self.cluster_1,
            "actions",
            self.get_object_action_with_process(self.cluster_1).id,
            "processes",
            process.id + 1,
        ].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "ACTION_PROCESS_NOT_FOUND")

    def test_retrieve_not_exist_step_in_process_fail(self):
        process = self.get_process(self.start_process(self.cluster_1))

        response = self.client.v2[
            self.cluster_1,
            "actions",
            self.get_object_action_with_process(self.cluster_1),
            "processes",
            process.id,
            "steps",
            process.steps.count() + 1,
        ].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "ACTION_PROCESS_STEP_NOT_FOUND")

    def test_retrieve_not_exist_step_in_not_exist_process_fail(self):
        process = self.get_process(self.start_process(self.cluster_1))

        response = self.client.v2[
            self.cluster_1,
            "actions",
            self.get_object_action_with_process(self.cluster_1),
            "processes",
            process.id + 1,
            "steps",
            process.steps.count() + 1,
        ].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "ACTION_PROCESS_NOT_FOUND")

    def test_submit_non_current_step(self):
        process = self.get_process(self.start_process(self.cluster_1))
        target_step = ProcessStep.objects.get(process_id=process.id, name="stage3_step1", display_name="Stage3.Step1")

        process_sync_key = process.sync_key
        payload = {
            "method": "submit_step",
            "params": {"processSyncKey": process_sync_key, "stepId": target_step.id},
        }

        response = self.client.v2[
            self.cluster_1,
            "actions",
            self.get_object_action_with_process(self.cluster_1),
            "processes",
            process.id,
            "operation",
        ].post(data=payload)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "ACTION_PROCESS_OPERATION_CONFLICT")
        self.assertEqual(response.json()["desc"], "Only current step can be submitted")

    def test_submit_previously_submitted_step(self):
        process = self.get_process(self.start_process(self.cluster_1))
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

        response = self.client.v2[
            self.cluster_1,
            "actions",
            self.get_object_action_with_process(self.cluster_1),
            "processes",
            process.id,
            "operation",
        ].post(data=payload)

        self.assertEqual(response.status_code, HTTP_200_OK)

        process.refresh_from_db()
        payload["params"]["processSyncKey"] = process.sync_key

        response = self.client.v2[
            self.cluster_1,
            "actions",
            self.get_object_action_with_process(self.cluster_1),
            "processes",
            process.id,
            "operation",
        ].post(data=payload)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "ACTION_PROCESS_OPERATION_CONFLICT")
        self.assertEqual(response.json()["desc"], "Only current step can be submitted")

    def test_create_process_with_broken_render_fail(self):
        response = self.client.v2[
            self.cluster_broken_process, "actions", self.action_broken_process.id, "processes"
        ].post(data={})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertIn("Extra inputs are not permitted", response.json()["desc"])

    def test_render_broken_configuration_step_success(self):
        # step is expected to be broken
        response = self.client.v2[
            self.cluster_broken_process, "actions", self.action_broken_configuration_step.id, "processes"
        ].post(data={})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        first_step = response.json()["stages"][0]["steps"][0]
        self.assertEqual(first_step["state"], "broken")

    def test_render_broken_operation_step_success(self):
        # step is expected to be broken
        response = self.client.v2[
            self.cluster_broken_process, "actions", self.action_broken_operation_step.id, "processes"
        ].post(data={})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        first_step = response.json()["stages"][0]["steps"][0]
        self.assertEqual(first_step["state"], "broken")

    def test_adcm_7150_second_step_broken(self):
        owner = self.cluster_broken_process
        action = Action.objects.get(name="broken_second_step")
        process: dict = self.initiate_process(owner, action).json()
        correct_step, broken_step = tuple(ProcessStep.objects.filter(process_id=process["id"]).order_by("id"))

        response = self.client.v2[owner, "actions", action, "processes", int(process["id"]), "operation"].post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": correct_step.pk,
                    "processSyncKey": process["syncKey"],
                    "configuration": {"config": {"string": "value"}, "adcmMeta": {}},
                },
            }
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
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
        process = self.initiate_process(owner, action).json()

        response = self.client.v2[owner, "actions", action, "run"].post(data={"process": {"id": process["id"]}})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT, response.json())
        self.assertIn("completed state", response.json()["desc"])

    def test_adcm_7298_submit_mapping_not_add_service_in_step_spec_success(self):
        self.add_services_to_cluster(["service_1"], cluster=self.cluster_3)
        component_1_s_1 = Component.objects.get(service__prototype__name="service_1", cluster=self.cluster_3)
        host_1 = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_3)

        process = self.get_process(self.start_process(self.cluster_3))
        cfg_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")
        target_mapping_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping", display_name="change mapping"
        )

        payload = {"config": {"integer_field": 200, "string_field": "str"}, "adcmMeta": {}}
        response = self.submit_config_step(
            obj=self.cluster_3, process=process, step_id=cfg_step.id, config_payload=payload
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(current_step_id, target_mapping_step.id)
        self.assertEqual(last_completed_step_id, cfg_step.id)

        inputs_count = ProcessStepInput.objects.filter(step_id=target_mapping_step.id).count()
        self.assertEqual(inputs_count, 0)

        process.refresh_from_db()
        endpoint = self.get_endpoint_to_processes(self.cluster_3) / process / "operation"
        hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_1_s_1.pk}]}
        response = endpoint.post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "step_id": target_mapping_step.id,
                    "process_sync_key": process.sync_key,
                    "host_component_map_delta": hc_delta,
                },
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        step_input = ProcessStepInput.objects.get(step_id=target_mapping_step.id)
        add_delta = {"add": [{"host_id": host_1.pk, "component_id": component_1_s_1.pk}]}
        expected_input_mapping = {"delta": {"remove": [], **add_delta}, "cumulative_delta": {"remove": [], **add_delta}}
        self.assertDictEqual(step_input.mapping, expected_input_mapping)
        self.assertIsNone(step_input.configuration)
        self.assertIsNone(step_input.job)

        process.refresh_from_db()
        self.assertTrue(process.current_step.id > target_mapping_step.id)

    def test_adcm_7295_submit_mapping_payload_validation(self):
        self.add_services_to_cluster(["service_1"], cluster=self.cluster_3)
        component_1_s_1 = Component.objects.get(service__prototype__name="service_1", cluster=self.cluster_3)
        host_1 = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_3)

        process = self.get_process(self.start_process(self.cluster_3))
        cfg_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")
        target_mapping_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping", display_name="change mapping"
        )

        payload = {"config": {"integer_field": 200, "string_field": "str"}, "adcmMeta": {}}
        response = self.submit_config_step(
            obj=self.cluster_3, process=process, step_id=cfg_step.id, config_payload=payload
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        current_step_id, last_completed_step_id = find_current_and_last_completed_steps(
            steps=ProcessStep.objects.filter(process_id=process.id)
        )
        self.assertEqual(current_step_id, target_mapping_step.id)
        self.assertEqual(last_completed_step_id, cfg_step.id)

        inputs_count = ProcessStepInput.objects.filter(step_id=target_mapping_step.id).count()
        self.assertEqual(inputs_count, 0)

        process.refresh_from_db()
        endpoint = self.get_endpoint_to_processes(self.cluster_3) / process / "operation"
        hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_1_s_1.pk}]}

        correct_payload = {
            "method": ProcessOperationType.SUBMIT,
            "params": {
                "stepId": target_mapping_step.id,
                "processSyncKey": process.sync_key,
                "hostComponentMapDelta": hc_delta,
            },
        }
        self.assertEqual(response.status_code, HTTP_200_OK)

        for param in ("stepId", "processSyncKey", "hostComponentMapDelta"):
            with self.subTest(f"{param} -> {param}New"):
                wrong_payload = deepcopy(correct_payload)
                wrong_payload["params"][f"{param}New"] = wrong_payload["params"].pop(param)

                response = endpoint.post(data=wrong_payload)
                self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

            with self.subTest(f"Missing `{param}`"):
                wrong_payload = deepcopy(correct_payload)
                del wrong_payload["params"][param]

                response = endpoint.post(data=wrong_payload)
                self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
