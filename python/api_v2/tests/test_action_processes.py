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
from typing import Any, Collection, Literal
from uuid import uuid4

from adcm.tests.client import APINode
from cm.converters import core_type_to_model, orm_object_to_core_descriptor, orm_object_to_core_type
from cm.legacy.issue import add_concern_to_object
from cm.legacy.services.action_process import repo
from cm.legacy.services.action_process.operations import (
    OperationContext,
    SubmitOperationStepParams,
    find_current_and_last_completed_steps,
    submit_step,
)
from cm.legacy.services.action_process.render_step import RenderStepContext, fill_step_spec
from cm.legacy.services.action_process.schema_validation import (
    Configuration,
    ProcessOperationType,
    SubmitConfigurationStepParams,
    SubmitStepPayload,
)
from cm.legacy.services.action_process.types import ProcessContext, ProcessState, ProcessStepState
from cm.legacy.services.bundle_alt.render import ActionArgs, TaskArgs
from cm.legacy.services.concern import create_issue
from cm.legacy.services.job.run.repo import ActionRepoImpl
from cm.models import (
    ADCM,
    Action,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    ConcernType,
    Host,
    HostComponent,
    Process,
    ProcessStep,
    ProcessStepInput,
    Service,
    TaskLog,
)
from cm.tests.mocks.task_runner import RunTaskMock
from core.dynamic_bundle.render import BundleRenderer
from core.legacy.job.runners import (
    ADCMSettings,
    AnsibleSettings,
    ConsulSettings,
    ExternalSettings,
    IntegrationsSettings,
)
from core.types import ActionTargetDescriptor, ADCMCoreType, CoreObjectDescriptor
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from jinja2 import Template
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
import core
import yaml

from api_v2.tests.base import BaseAPITestCase

PATCH_PATH = "cm.legacy.services.action_process.operations.start_task"


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
        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster_1).get()
        self.component_1 = Component.objects.get(service=self.service_1, prototype__name="component_1")

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
                url=settings.CONSUL_URL, datacenter=settings.CONSUL_DATACENTER, cacert_file=settings.CONSUL_CACERT_FILE
            ),
        )

        bundle_hc_restrictions_dir = self.test_bundles_dir / "wizard_mapping_restrictions"
        bundle = self.add_bundle(source_dir=bundle_hc_restrictions_dir)
        self.cluster_with_mapping_restrictions = self.add_cluster(
            bundle=bundle, name="cluster with mapping restrictions"
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

    def start_process(self, obj: Cluster | Service | Component, action: Action | None = None):
        endpoint = self.get_endpoint_to_processes(obj, action=action)
        response = endpoint.post(data={})
        return response.json()["id"]

    def get_endpoint_to_processes(self, obj: Cluster | Service | Component, action: Action | None = None):
        action_ = action or self.get_object_action_with_process(obj)
        return self.client.v2[obj, "actions", action_.pk, "processes"]

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

    def cleanup_process_hc_service(self, cluster_id: int, service_ids: list[int], process_id: int):
        HostComponent.objects.filter(cluster_id=cluster_id).delete()
        for service in Service.objects.filter(cluster_id=cluster_id, id__in=service_ids):
            response = self.client.v2[service].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        steps_qs = ProcessStep.objects.filter(process_id=process_id)
        ProcessStepInput.objects.filter(step_id__in=steps_qs.values_list("id", flat=True)).delete()
        steps_qs.delete()
        Process.objects.get(id=process_id).delete()

    @staticmethod
    def submit_step(process_id: int, object_: CoreObjectDescriptor, payload: SubmitStepPayload, action_id: int):
        process = repo.retrieve_process(process_id=process_id)
        action_info = ActionRepoImpl.get_action(id=action_id)
        object_orm = core_type_to_model(object_.type).objects.get(id=object_.id)
        context = OperationContext(
            process_context=ProcessContext(
                action=action_info,
                action_orm=Action.objects.get(id=action_id),
                owner=object_,
                owner_orm=object_orm,
                target=ActionTargetDescriptor(id=object_.id, type=object_.type),
                target_orm=object_orm,
            ),
            config_processor=lambda x, _: core.config.Configuration(values=x.config),
        )

        # don't copy this implementation, it's a hack, may not work in most cases
        from adcm.dependencies import prepare_container

        container = prepare_container()

        submit_step(
            process=process,
            payload=payload,
            context=context,
            new_process_sync_key=uuid4(),
            config_service=container.get(core.config.ConfigService),
            job_service=container.get(core.job.JobService),
            bundle_renderer=container.get(BundleRenderer[ActionArgs, TaskArgs]),
        )

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
                            target_id=obj.pk, target_type=orm_object_to_core_type(obj).value
                        ).count(),
                        1,
                    )

                    process = Process.objects.get(target_id=obj.pk, target_type=orm_object_to_core_type(obj).value)

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
                        "description": "",
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

                    response_template = (
                        self.test_files_dir / "responses" / "action_process" / "retrieve_config_step.yml"
                    )
                    expected_response = render_template(file=response_template, context={"step_id": target_step.id})
                    self.assertDictEqual(response.json(), expected_response)

    def test_retrieve_operation_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        action = self.get_object_action_with_process(self.cluster_1)

        config = {"integer_field": 10, "string_field": "string"}

        payload = SubmitStepPayload(
            method=ProcessOperationType.SUBMIT,
            params=SubmitConfigurationStepParams(
                process_sync_key=process.sync_key,
                step_id=process.current_step_id,
                configuration=Configuration(config=config, adcm_meta={}),
            ),
        )

        self.submit_step(
            process_id=process.id,
            object_=CoreObjectDescriptor(id=self.cluster_1.id, type=ADCMCoreType.CLUSTER),
            action_id=action.id,
            payload=payload,
        )

        process.refresh_from_db()

        config = {"int": 10}

        payload = SubmitStepPayload(
            method=ProcessOperationType.SUBMIT,
            params=SubmitConfigurationStepParams(
                process_sync_key=process.sync_key,
                step_id=process.current_step_id,
                configuration=Configuration(config=config, adcm_meta={}),
            ),
        )

        self.submit_step(
            process_id=process.id,
            object_=CoreObjectDescriptor(id=self.cluster_1.id, type=ADCMCoreType.CLUSTER),
            action_id=action.id,
            payload=payload,
        )

        process.refresh_from_db()

        current_step_id = process.current_step_id
        self.client.login(**self.test_user_credentials)

        with self.subTest("No view permissions"):
            response = self.client.v2[
                self.cluster_1,
                "actions",
                self.get_object_action_with_process(self.cluster_1).pk,
                "processes",
                process.id,
                "steps",
                current_step_id,
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
                    current_step_id,
                ].get()
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.client.login(username="admin", password="admin")

        with self.subTest("All permissions"):
            response = self.client.v2[
                self.cluster_1,
                "actions",
                self.get_object_action_with_process(self.cluster_1).pk,
                "processes",
                process.id,
                "steps",
                current_step_id,
            ].get()

            self.assertEqual(response.status_code, HTTP_200_OK)

            target_step = ProcessStep.objects.get(id=current_step_id)

            expected_spec = [
                {
                    "name": "sleep_script",
                    "params": {"test_params": [self.cluster_1.state]},
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

            response_template = self.test_files_dir / "responses" / "action_process" / "retrieve_operation_step.yml"
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

    def test_submit_operation_hc_apply_fail(self):
        process = self.get_process(self.start_process(self.cluster_2))
        action = self.get_object_action_with_process(self.cluster_2)

        config = {"integer_field": 10, "string_field": "string"}

        payload = SubmitStepPayload(
            method=ProcessOperationType.SUBMIT,
            params=SubmitConfigurationStepParams(
                process_sync_key=process.sync_key,
                step_id=process.current_step_id,
                configuration=Configuration(config=config, adcm_meta={}),
            ),
        )

        self.submit_step(
            process_id=process.id,
            object_=CoreObjectDescriptor(id=self.cluster_2.id, type=ADCMCoreType.CLUSTER),
            action_id=action.id,
            payload=payload,
        )

        process.refresh_from_db()

        action_id = self.process_action_of_cluster.pk

        # don't copy this implementation, it's a hack, may not work in most cases
        from adcm.dependencies import prepare_container

        container = prepare_container()

        fill_step_spec(
            step_id=process.current_step_id,
            context=RenderStepContext(
                process_id=process.id,
                process_context=ProcessContext(
                    action=ActionRepoImpl.get_action(id=action_id),
                    action_orm=Action.objects.get(id=action_id),
                    owner=orm_object_to_core_descriptor(self.cluster_2),
                    owner_orm=self.cluster_2,
                    target=ActionTargetDescriptor(id=self.cluster_2.id, type=ADCMCoreType.CLUSTER),
                    target_orm=self.cluster_2,
                ),
            ),
            bundle_renderer=container.get(BundleRenderer[ActionArgs, TaskArgs]),
        )
        step = ProcessStep.objects.get(id=process.current_step_id)
        self.assertEqual(step.state, ProcessStepState.BROKEN.value)

    def test_submit_operation_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        action = self.get_object_action_with_process(self.cluster_1)
        initial_sync_key = process.sync_key

        # TODO: duplicate code, need rework
        config = {"integer_field": 10, "string_field": "string"}

        payload = SubmitStepPayload(
            method=ProcessOperationType.SUBMIT,
            params=SubmitConfigurationStepParams(
                process_sync_key=process.sync_key,
                step_id=process.current_step_id,
                configuration=Configuration(config=config, adcm_meta={}),
            ),
        )

        self.submit_step(
            process_id=process.id,
            object_=CoreObjectDescriptor(id=self.cluster_1.id, type=ADCMCoreType.CLUSTER),
            action_id=action.id,
            payload=payload,
        )

        process.refresh_from_db()

        config = {"int": 10}

        payload = SubmitStepPayload(
            method=ProcessOperationType.SUBMIT,
            params=SubmitConfigurationStepParams(
                process_sync_key=process.sync_key,
                step_id=process.current_step_id,
                configuration=Configuration(config=config, adcm_meta={}),
            ),
        )

        self.submit_step(
            process_id=process.id,
            object_=CoreObjectDescriptor(id=self.cluster_1.id, type=ADCMCoreType.CLUSTER),
            action_id=action.id,
            payload=payload,
        )

        process.refresh_from_db()

        operation_step_id = process.current_step_id
        self.client.login(**self.test_user_credentials)

        with self.subTest("No view permissions"):
            response = self.client.v2[
                self.cluster_1, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {"step_id": operation_step_id, "process_sync_key": process.sync_key},
                }
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("No run permissions"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
                response = self.client.v2[
                    self.cluster_1, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
                ].post(
                    data={
                        "method": ProcessOperationType.SUBMIT,
                        "params": {"step_id": operation_step_id, "process_sync_key": process.sync_key},
                    }
                )
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("All permissions"):
            self.client.login(username="admin", password="admin")

            response = self.client.v2[
                self.cluster_1, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {"step_id": operation_step_id, "process_sync_key": process.sync_key},
                }
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["id"], process.id)
            self.assertEqual(response.json()["createdAt"], str(process.created_at.isoformat().replace("+00:00", "Z")))
            self.assertEqual(sum(len(stage["steps"]) for stage in response.json()["stages"]), process.steps.count())

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

    def test_submit_mapping_success(self):
        self.add_services_to_cluster(["service_1", "service_2", "service_3"], cluster=self.cluster_3)
        component_1_s_1 = Component.objects.filter(service__prototype__name="service_1", cluster=self.cluster_3).first()
        component_1_s_2 = Component.objects.filter(service__prototype__name="service_2", cluster=self.cluster_3).first()
        component_1_s_3 = Component.objects.filter(service__prototype__name="service_3", cluster=self.cluster_3).first()
        host_1 = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_3)
        host_2 = self.add_host(provider=self.provider, fqdn="host-2", cluster=self.cluster_3)
        host_3 = self.add_host(provider=self.provider, fqdn="host-3", cluster=self.cluster_3)

        process = self.get_process(self.start_process(self.cluster_3))
        action = self.get_object_action_with_process(self.cluster_3)

        config = {"integer_field": 10, "string_field": "string"}

        payload = SubmitStepPayload(
            method=ProcessOperationType.SUBMIT,
            params=SubmitConfigurationStepParams(
                process_sync_key=process.sync_key,
                step_id=process.current_step_id,
                configuration=Configuration(config=config, adcm_meta={}),
            ),
        )

        self.submit_step(
            process_id=process.id,
            object_=CoreObjectDescriptor(id=self.cluster_3.id, type=ADCMCoreType.CLUSTER),
            action_id=action.id,
            payload=payload,
        )

        process.refresh_from_db()

        current_step_id = process.current_step_id

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

            response = self.client.v2[
                self.cluster_3, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
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

            response = self.client.v2[
                self.cluster_3, "actions", self.process_action_of_cluster.pk, "processes", process.id, "operation"
            ].post(
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

    def test_wizard_action_run_with_object_concern_success(self):
        issue = create_issue(
            owner=CoreObjectDescriptor(id=self.cluster_1.id, type=ADCMCoreType.CLUSTER), cause=ConcernCause.CONFIG
        )
        add_concern_to_object(object_=self.cluster_1, concern=issue)

        endpoint = self.get_endpoint_to_processes(self.cluster_1)
        response = endpoint.post(data={})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertIn(f"object {self.cluster_1} has issues", response.json()["desc"])

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

        with self.subTest("Without adcmMeta"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            del payload["adcmMeta"]

            response = self.submit_config_step(
                obj=self.config_cluster, process=process, step_id=step.id, config_payload=payload
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        with self.subTest("With empty adcmMeta"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            payload["adcmMeta"] = {}

            response = self.submit_config_step(
                obj=self.config_cluster, process=process, step_id=step.id, config_payload=payload
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        with self.subTest("With empty /agroup meta"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            payload["adcmMeta"]["/agroup"] = {}

            response = self.submit_config_step(
                obj=self.config_cluster, process=process, step_id=step.id, config_payload=payload
            )

        with self.subTest("Without required field"):
            self.make_step_current(step=step)
            payload = deepcopy(base_payload)
            del payload["config"]["integer_field"]

            response = self.submit_config_step(
                obj=self.config_cluster, process=process, step_id=step.id, config_payload=payload
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

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
        component_1_s1 = Component.objects.get(
            prototype__name="component_1_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
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
        hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_1_s1.pk}]}
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
        add_delta = {"add": [{"host_id": host_1.pk, "component_id": component_1_s1.pk}]}
        expected_input_mapping = {"delta": {"remove": [], **add_delta}, "cumulative_delta": {"remove": [], **add_delta}}
        self.assertDictEqual(step_input.mapping, expected_input_mapping)
        self.assertIsNone(step_input.configuration)
        self.assertIsNone(step_input.job)

        process.refresh_from_db()
        self.assertTrue(process.current_step.id > target_mapping_step.id)

    def test_adcm_7295_submit_mapping_payload_validation(self):
        self.add_services_to_cluster(["service_1"], cluster=self.cluster_3)
        component_1_s1 = Component.objects.get(
            prototype__name="component_1_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
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
        hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_1_s1.pk}]}

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

    def test_adcm_7151_task_display_name_success(self):
        action = Action.objects.get(name="wizard_operation_as_first", prototype=self.cluster_1.prototype)
        process = self.get_process(self.start_process(self.cluster_1, action=action))
        expected_display_name = f"{action.display_name} (find me In here)"
        with RunTaskMock(run_patch_path=PATCH_PATH) as run_task:
            self.submit_step(
                process_id=process.pk,
                action_id=action.pk,
                object_=CoreObjectDescriptor(id=self.cluster_1.pk, type=ADCMCoreType.CLUSTER),
                payload=SubmitStepPayload(
                    method=ProcessOperationType.SUBMIT,
                    params=SubmitOperationStepParams(
                        step_id=process.current_step.pk, process_sync_key=process.sync_key
                    ),
                ),
            )
        task_with_step = run_task.target_task
        self.assertIsNotNone(task_with_step)

        response = self.client.v2[task_with_step].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["displayName"], expected_display_name)

        # get tasks list
        response = (self.client.v2 / "tasks").get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        response = response.json()["results"]

        task_with_step_response = [task for task in response if task["id"] == task_with_step.id][0]
        self.assertEqual(task_with_step_response["displayName"], expected_display_name)

    def test_adcm_7302_submit_mapping_step_restrictions_fail(self):
        self.add_services_to_cluster(["service_1", "service_2"], cluster=self.cluster_3)
        component_1_s1 = Component.objects.get(
            prototype__name="component_1_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
        component_free_s1 = Component.objects.get(
            prototype__name="free_component_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
        component_1_s2 = Component.objects.get(
            prototype__name="component_1_s2", service__prototype__name="service_2", cluster=self.cluster_3
        )
        host_1 = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_3)

        process = self.get_process(self.start_process(self.cluster_3))
        cfg_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")
        first_mapping_step = ProcessStep.objects.get(
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

        process.refresh_from_db()
        endpoint = self.get_endpoint_to_processes(self.cluster_3) / process / "operation"

        with self.subTest("Submit `add not specified` payload"):
            hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_free_s1.pk}]}
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": first_mapping_step.id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": hc_delta,
                },
            }
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
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
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": first_mapping_step.id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": hc_delta,
                },
            }
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
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
            payload = {
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "stepId": first_mapping_step.id,
                    "processSyncKey": process.sync_key,
                    "hostComponentMapDelta": hc_delta,
                },
            }

            self.set_hostcomponent(cluster=self.cluster_3, entries=[(host_1, component_1_s2)])
            response = endpoint.post(data=payload)  # submit add already existing mapping
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            expected_response = {
                "code": "ACTION_PROCESS_OPERATION_CONFLICT",
                "level": "error",
                "desc": "Add operation is not allowed for "
                f'"{component_1_s2.service.prototype.name}.{component_1_s2.prototype.name}". Already mapped.',
            }
            self.assertDictEqual(response.json(), expected_response)

        HostComponent.objects.filter(cluster_id=self.cluster_3.id).delete()
        response = endpoint.post(data=payload)  # proceed to the next step
        self.assertEqual(response.status_code, HTTP_200_OK)

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
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            expected_response = {
                "code": "ACTION_PROCESS_OPERATION_CONFLICT",
                "level": "error",
                "desc": "Remove operation is not allowed for "
                f'"{component_1_s1.service.prototype.name}.{component_1_s1.prototype.name}". Not mapped.',
            }
            self.assertDictEqual(response.json(), expected_response)

    def test_adcm_7393_invalid_mapping_template_fail(self):
        bundle_dir = self.test_bundles_dir / "wizard_broken_hc_step"
        bundle = self.add_bundle(source_dir=bundle_dir)
        cluster = self.add_cluster(bundle=bundle, name="cluster_with_broken_hc_step")

        action_first_step_fail = Action.objects.get(prototype=cluster.prototype, name="wizard_first_step_broken")
        action_second_step_fail = Action.objects.get(prototype=cluster.prototype, name="wizard_second_step_broken")

        # first step
        response = self.initiate_process(owner=cluster, action=action_first_step_fail).json()
        process_id, current_step_id = response["id"], response["currentStep"]
        target_step = ProcessStep.objects.get(process_id=process_id, name="first_broken_mapping_step")

        self.assertEqual(target_step.id, current_step_id)
        self.assertEqual(target_step.state, ProcessStepState.BROKEN)

        # second step after submitting first
        response = self.initiate_process(owner=cluster, action=action_second_step_fail).json()
        process_id, current_step_id = response["id"], response["currentStep"]
        config_step = ProcessStep.objects.get(id=current_step_id, process_id=process_id, name="first_config_step")
        target_step = ProcessStep.objects.get(process_id=process_id, name="second_broken_mapping_step")
        process = Process.objects.get(id=process_id)

        self.assertEqual(config_step.id, current_step_id)
        endpoint = self.client.v2[cluster, "actions", action_second_step_fail.pk, "processes"] / process / "operation"
        payload = {
            "method": "submit_step",
            "params": {
                "processSyncKey": process.sync_key,
                "stepId": config_step.id,
                "configuration": {"config": {"float": 0.3}, "adcmMeta": {}},
            },
        }
        response = endpoint.post(data=payload)
        self.assertEqual(response.status_code, HTTP_200_OK)
        config_step.refresh_from_db()
        self.assertEqual(config_step.state, ProcessStepState.COMPLETED)

        target_step.refresh_from_db()
        self.assertEqual(response.json()["currentStep"], target_step.id)
        self.assertEqual(target_step.state, ProcessStepState.BROKEN)

    def _test_adcm_7308_submit_mapping_component_constraint(
        self,
        cluster: Cluster,
        action: str,
        service: str,
        component: str,
        initial_hc: list[Host],
        hc: dict[Literal["add", "remove"], list[Host]],
    ):
        action = Action.objects.get(prototype=cluster.prototype, name=action)
        service = self.add_services_to_cluster(service_names=[service], cluster=cluster).get()
        component = Component.objects.get(prototype__name=component, service=service, cluster=cluster)

        # set initial hc mapping
        initial_hc = initial_hc or []
        response = self.client.v2[cluster, "mapping"].post(
            data=[{"hostId": host.pk, "componentId": component.pk} for host in initial_hc],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())

        # init process
        response = self.client.v2[cluster, "actions", action.pk, "processes"].post()
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        process = self.get_process(process_id=response.json()["id"])
        step = process.steps.get()

        # submit mapping step
        operations_endpoint = self.client.v2[cluster, "actions", action.id, "processes", process.id, "operation"]
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

        response = operations_endpoint.post(data=payload)
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        response = response.json()
        self.assertEqual(response["code"], "COMPONENT_CONSTRAINT_ERROR")
        self.assertEqual(response["level"], "error")
        self.assertRegex(response["desc"], r'Component ".*" of service ".*" has unsatisfied constraint:')

        # cleanup
        self.cleanup_process_hc_service(cluster_id=cluster.id, service_ids=[service.id], process_id=process.id)

    def test_adcm_7308_submit_mapping_component_constraints_fail(self):
        cluster = self.cluster_with_mapping_restrictions
        host_1 = self.add_host(provider=self.provider, fqdn="host-1", cluster=cluster)
        host_2 = self.add_host(provider=self.provider, fqdn="host-2", cluster=cluster)
        host_3 = self.add_host(provider=self.provider, fqdn="host-3", cluster=cluster)

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
            service = self.add_services_to_cluster(
                service_names=["service_with_zero_one_component_constraint"], cluster=cluster
            ).get()
            component = Component.objects.get(prototype__name="zero_one", service=service, cluster=cluster)

            # init process
            response = self.client.v2[cluster, "actions", action.pk, "processes"].post()
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            process = self.get_process(process_id=response.json()["id"])
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
        service = self.add_services_to_cluster(["service_with_zero_one_component_constraint"], cluster=cluster).get()
        component = Component.objects.get(prototype__name="zero_one", service=service, cluster=cluster)
        action = Action.objects.get(name="action_c_zero_one", prototype=cluster.prototype)
        host = self.add_host(provider=self.provider, fqdn="host-1", cluster=cluster)

        # init process
        response = self.client.v2[cluster, "actions", action.pk, "processes"].post()
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        process = self.get_process(process_id=response.json()["id"])

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
        self, cluster: Cluster, action_name: str
    ) -> tuple[APINode, Process]:
        action = Action.objects.get(name=action_name, prototype=cluster.prototype)
        response = self.client.v2[cluster, "actions", action.pk, "processes"].post()
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        process = self.get_process(process_id=response.json()["id"])

        return self.client.v2[cluster, "actions", action.id, "processes", process.id, "operation"], process

    def test_7313_submit_mapping_step_dependencies_fail(self):
        cluster = self.cluster_with_mapping_restrictions
        host = self.add_host(provider=self.provider, fqdn="host-1", cluster=cluster)

        with self.subTest("Service requires service"):
            endpoint, process = self._7313_prepare_env_get_operation_endpoint_and_process(
                cluster=cluster, action_name="action_service_requires_service"
            )
            service = self.add_services_to_cluster(service_names=["service_requires_service"], cluster=cluster).get()
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
            required_service = self.add_services_to_cluster(service_names=["service_required"], cluster=cluster).get()
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_200_OK)

            self.cleanup_process_hc_service(
                cluster_id=cluster.id, service_ids=[service.id, required_service.id], process_id=process.id
            )

        with self.subTest("Service requires component"):
            endpoint, process = self._7313_prepare_env_get_operation_endpoint_and_process(
                cluster=cluster, action_name="action_service_requires_component"
            )
            service = self.add_services_to_cluster(service_names=["service_requires_component"], cluster=cluster).get()
            component = Component.objects.get(prototype__name="component_1", service=service, cluster=cluster)
            service_with_required_component = self.add_services_to_cluster(
                service_names=["service_with_component_required"], cluster=cluster
            ).get()
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
            host_2 = self.add_host(provider=self.provider, fqdn="host-2", cluster=cluster)

            endpoint, process = self._7313_prepare_env_get_operation_endpoint_and_process(
                cluster=cluster, action_name="action_bound_component"
            )
            service = self.add_services_to_cluster(
                service_names=["service_with_bound_component"], cluster=cluster
            ).get()
            component = Component.objects.get(prototype__name="bound_component", service=service, cluster=cluster)
            bound_target_service = self.add_services_to_cluster(
                service_names=["bound_target_service"], cluster=cluster
            ).get()
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
        self.add_services_to_cluster(["service_1", "service_2"], cluster=self.cluster_3)
        component_1_s1 = Component.objects.get(
            prototype__name="component_1_s1", service__prototype__name="service_1", cluster=self.cluster_3
        )
        component_1_s2 = Component.objects.get(
            prototype__name="component_1_s2", service__prototype__name="service_2", cluster=self.cluster_3
        )
        host_1 = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_3)
        process = self.get_process(self.start_process(self.cluster_3))

        # submit config step
        cfg_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")
        payload = {"config": {"integer_field": 200, "string_field": "str"}, "adcmMeta": {}}
        response = self.submit_config_step(
            obj=self.cluster_3, process=process, step_id=cfg_step.id, config_payload=payload
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

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
        endpoint = self.get_endpoint_to_processes(self.cluster_3) / process / "operation"

        first_mapping_step_hc_delta = {"add": [{"hostId": host_1.pk, "componentId": component_1_s1.pk}]}
        payload = {
            "method": ProcessOperationType.SUBMIT,
            "params": {
                "stepId": first_mapping_step.id,
                "processSyncKey": process.sync_key,
                "hostComponentMapDelta": first_mapping_step_hc_delta,
            },
        }
        response = endpoint.post(data=payload)
        self.assertEqual(response.status_code, HTTP_200_OK)

        # retrieve second mapping step
        second_mapping_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_mapping_again", display_name="change mapping again"
        )
        endpoint = self.get_endpoint_to_processes(self.cluster_3) / process / "steps" / second_mapping_step
        response = endpoint.get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        response = response.json()
        self.assertIsNone(response["delta"])
        expected_cumulative_delta = {"remove": [], **first_mapping_step_hc_delta}
        self.assertDictEqual(response["cumulativeDelta"], expected_cumulative_delta)

        # submit second mapping step
        process.refresh_from_db()
        endpoint = self.get_endpoint_to_processes(self.cluster_3) / process / "operation"

        second_mapping_step_hc_delta = {  # add s2c2, remove s1c1 (reverts first step add)
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
        response = endpoint.post(data=payload)
        self.assertEqual(response.status_code, HTTP_200_OK)

        # retrieve second mapping step again
        endpoint = self.get_endpoint_to_processes(self.cluster_3) / process / "steps" / second_mapping_step
        response = endpoint.get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        response = response.json()
        self.assertDictEqual(response["delta"], second_mapping_step_hc_delta)
        expected_cumulative_delta = {"add": second_mapping_step_hc_delta["add"], "remove": []}
        self.assertDictEqual(response["cumulativeDelta"], expected_cumulative_delta)

    def test_adcm_7551_process_on_host_action(self):
        cluster, service, component = self.cluster_1, self.service_1, self.component_1
        host = self.add_host(provider=self.provider, fqdn="test-host", cluster=cluster)

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

        host_actions = (host_action_from_cluster, host_action_from_service, host_action_from_component)

        for action in host_actions:
            with self.subTest(f"Retrieve {action=}"):
                response = self.client.v2[cluster, "hosts", host, "actions", action].get()
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertListEqual(response.json()["processes"], [])

        expected_step_spec = {
            "step_1_config": [
                {
                    "groups": {},
                    "hierarchy": {"child_groups": {}, "fields": ["float"], "rule": "all"},
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
                        }
                    },
                },
                {"values": {"/float": 0.1}, "selection": {}, "activation": {}},
            ],
            "step_2_mapping": [{"service": service.name, "component": component.name, "operation": "remove"}],
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
        for action in host_actions:
            with self.subTest(f"Process on {action=}"):
                host_concerns = ConcernItem.objects.filter(
                    owner_id=host.id,
                    owner_type=ContentType.objects.get_for_model(host),
                    cause=ConcernCause.CONFIGURING_PROCESS,
                )
                self.assertEqual(host_concerns.count(), 0)

                action_endpoint = self.client.v2[cluster, "hosts", host, "actions", action]
                processes_endpoint = action_endpoint / "processes"
                response = processes_endpoint.post(data={})
                self.assertEqual(response.status_code, HTTP_201_CREATED)
                host_concerns = ConcernItem.objects.filter(
                    owner_id=host.id,
                    owner_type=ContentType.objects.get_for_model(host),
                    cause=ConcernCause.CONFIGURING_PROCESS,
                )
                self.assertEqual(host_concerns.count(), 1)
                concern = host_concerns.get()
                self.assertEqual(concern.type, ConcernType.FLAG)
                self.assertEqual(concern.name, "action_process_running")

                process = Process.objects.get(id=response.json()["id"])
                self.assertEqual(process.state, ProcessState.CREATED.value)

                # first config step
                step_1_config = ProcessStep.objects.get(process=process, name="step_1_config")
                self.assertEqual(step_1_config.state, ProcessStepState.CREATED.value)
                self.assertListEqual(step_1_config.step_spec, expected_step_spec[step_1_config.name])

                operation_endpoint = processes_endpoint / process / "operation"
                response = operation_endpoint.post(
                    data={
                        "method": ProcessOperationType.SUBMIT,
                        "params": {
                            "processSyncKey": process.sync_key,
                            "stepId": step_1_config.id,
                            "configuration": {"config": {"float": 0.4}, "adcmMeta": {}},
                        },
                    }
                )
                self.assertEqual(response.status_code, HTTP_200_OK)

                step_1_config.refresh_from_db()
                self.assertEqual(step_1_config.state, ProcessStepState.COMPLETED)

                # second mapping step
                process.refresh_from_db()
                step_2_mapping = ProcessStep.objects.get(process=process, name="step_2_mapping")
                self.assertListEqual(step_2_mapping.step_spec, expected_step_spec[step_2_mapping.name])
                self.assertEqual(step_2_mapping.state, ProcessStepState.CREATED.value)

                response = operation_endpoint.post(
                    data={
                        "method": ProcessOperationType.SUBMIT,
                        "params": {
                            "processSyncKey": process.sync_key,
                            "stepId": step_2_mapping.id,
                            "hostComponentMapDelta": {"remove": [{"hostId": host.id, "componentId": component.id}]},
                        },
                    }
                )
                self.assertEqual(response.status_code, HTTP_200_OK)

                step_2_mapping.refresh_from_db()
                self.assertEqual(step_2_mapping.state, ProcessStepState.COMPLETED)

                # third operation step
                process.refresh_from_db()
                step_3_operation = ProcessStep.objects.get(process=process, name="step_3_operation")
                self.assertListEqual(step_3_operation.step_spec, expected_step_spec[step_3_operation.name])
                self.assertEqual(step_3_operation.state, ProcessStepState.CREATED.value)

                with RunTaskMock(run_patch_path=PATCH_PATH) as run_task:
                    response = operation_endpoint.post(
                        data={
                            "method": ProcessOperationType.SUBMIT,
                            "params": {"processSyncKey": process.sync_key, "stepId": step_3_operation.id},
                        }
                    )
                    self.assertEqual(response.status_code, HTTP_200_OK)

                run_task.runner.run(run_task.target_task.id)

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
                response = operation_endpoint.post(
                    data={"method": ProcessOperationType.COMPLETE, "params": {"processSyncKey": process.sync_key}}
                )
                self.assertEqual(response.status_code, HTTP_200_OK)

                process.refresh_from_db()
                self.assertEqual(process.state, ProcessState.COMPLETED.value)

                host_concerns = ConcernItem.objects.filter(
                    owner_id=host.id,
                    owner_type=ContentType.objects.get_for_model(host),
                    cause=ConcernCause.CONFIGURING_PROCESS,
                )
                self.assertEqual(host_concerns.count(), 0)

                # run process action
                with RunTaskMock() as run_task:
                    response = (action_endpoint / "run").post(data={"process": {"id": process.id}})
                    self.assertEqual(response.status_code, HTTP_200_OK)

                # remove job lock
                ConcernItem.objects.filter(
                    name="job_lock", owner_id=host.id, owner_type=ContentType.objects.get_for_model(host)
                ).delete()
