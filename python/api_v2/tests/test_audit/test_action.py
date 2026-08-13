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

from collections.abc import Iterable
from dataclasses import asdict
from typing import Literal

from audit.models import AuditLogOperationType
from cm.converters import orm_object_to_action_target_type, orm_object_to_core_descriptor
from cm.impl.job.repo import JobRepo
from cm.legacy.services.action_process.render_step import RenderStepContext, fill_step_spec
from cm.legacy.services.action_process.schema_validation import ProcessOperationType
from cm.legacy.services.action_process.types import ProcessContext, ProcessStepState
from cm.legacy.services.bundle_alt.render import ActionArgs, TaskArgs
from cm.models import Action, Cluster, Component, ConcernItem, Process, ProcessStep, ProcessStepInput, Service
from core.dynamic_bundle.render import BundleRenderer
from core.types import ActionTargetDescriptor
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from tests.suites import ADCMDjangoAPISuite
import core


class TestActionProcessAudit(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cluster_bundle = cls.test_bundles_dir / "wizard_action"
        cls.bundle_1 = cls.uc.upload_bundle(src=cluster_bundle)
        cls.cluster_1 = cls.uc.add_cluster(bundle=cls.bundle_1, name="cluster_1", description="cluster_1")

        cls.service_1, *_ = cls.uc.add_services_to_cluster(["service_1"], cluster=cls.cluster_1)
        cls.component_1 = Component.objects.filter(service=cls.service_1).first()

        cls.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        cls.test_user = cls.uc.create_user(**cls.test_user_credentials)

    def get_object_action_with_process(self, obj: Cluster | Service | Component) -> Action:
        return Action.objects.get(name="wizard_jinja", prototype=obj.prototype)

    def start_process(self, obj: Cluster | Service | Component):
        endpoint = self.get_endpoint_to_processes(obj)
        response = endpoint.post(data={})
        return response.json()["id"]

    def get_endpoint_to_processes(self, obj: Cluster | Service | Component):
        return self.client.v2[obj, "actions", self.get_object_action_with_process(obj).pk, "processes"]

    def get_process(self, process_id: int) -> Process:
        return Process.objects.get(pk=process_id)

    def fill_steps_for_process(
        self,
        process_id: int,
        test_spec: list[dict],
        test_input: dict[Literal["config", "attr"], dict],
        previous_step_names: Iterable[str],
    ) -> None:
        # Fill previous steps' `step_spec`, create inputs for them
        for step in ProcessStep.objects.filter(process_id=process_id, name__in=previous_step_names):
            step.step_spec = test_spec
            step.state = ProcessStepState.COMPLETED
            step.save(update_fields=["step_spec", "state"])
            ProcessStepInput.objects.create(step_id=step.id, job=None, configuration=test_input)

    def test_audit_record_process_operation(self):
        test_spec = (
            core.config.spec.FullSpec.from_parameters(
                core.config.spec.p.StringParameter(identifier=core.config.spec.p.Identifier(name="spec", full="/spec"))
            ).model_dump(),
            asdict(core.config.Defaults()),
        )
        test_input, previous_step_names = (
            {"values": {}, "attributes": {}},
            {"stage1_step1", "stage2_step1"},
        )

        process = self.get_process(self.start_process(self.cluster_1))
        action = self.get_object_action_with_process(self.cluster_1)
        target_operation_step = ProcessStep.objects.get(
            process_id=process.id, name="stage1_step1", display_name="Stage1.Step1"
        )

        with self.subTest(f"submit process step for {self.cluster_1} fail (bad request)"):
            response = self.client.v2[self.cluster_1, "actions", action.pk, "processes", process.id, "operation"].post()

            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            self.check_last_audit_record(
                operation_name=f"Operation for process {process.id} of action {action.display_name}",
                operation_result="fail",
                operation_type=AuditLogOperationType.UPDATE,
                **self.prepare_audit_object_arguments(expected_object=self.cluster_1, is_deleted=False),
                user__username="admin",
            )

        with self.subTest(f"submit process step for {self.cluster_1} fail (no permissions"):
            self.client.login(**self.test_user_credentials)

            response = self.client.v2[self.cluster_1, "actions", action.pk, "processes", process.id, "operation"].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {"step_id": target_operation_step.id, "process_sync_key": process.sync_key},
                }
            )

            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
            self.check_last_audit_record(
                operation_name=f"Operation {ProcessOperationType.SUBMIT.value} {target_operation_step.id} "
                f"for process {process.id} of action {action.display_name}",
                operation_result="denied",
                operation_type=AuditLogOperationType.UPDATE,
                **self.prepare_audit_object_arguments(expected_object=self.cluster_1, is_deleted=False),
                user__username=self.test_user_credentials["username"],
            )

        self.client.login(username="admin", password="admin")

        for obj in (self.cluster_1, self.service_1, self.component_1):
            with self.subTest(f"submit process step for {obj} success"):
                process = self.get_process(self.start_process(obj))
                target_operation_step = ProcessStep.objects.get(
                    process_id=process.id, name="stage2_step2", display_name="Stage2.Step2"
                )
                self.fill_steps_for_process(process.id, test_spec, test_input, previous_step_names)
                action = self.get_object_action_with_process(obj)

                # render step
                fill_step_spec(
                    step_id=target_operation_step.id,
                    context=RenderStepContext(
                        process_id=process.id,
                        process_context=ProcessContext(
                            action=JobRepo().get_action(id=action.id),
                            action_orm=action,
                            owner=orm_object_to_core_descriptor(obj),
                            owner_orm=obj,
                            target=ActionTargetDescriptor(id=obj.id, type=orm_object_to_action_target_type(obj)),
                            target_orm=obj,
                        ),
                    ),
                    bundle_renderer=self.container.get(BundleRenderer[ActionArgs, TaskArgs]),
                    wizard_repo=self.container.get(core.action.wizard.WizardRepoI),
                )

                response = self.client.v2[obj, "actions", action.pk, "processes", process.id, "operation"].post(
                    data={
                        "method": ProcessOperationType.SUBMIT,
                        "params": {"step_id": target_operation_step.id, "process_sync_key": process.sync_key},
                    }
                )

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.check_last_audit_record(
                    operation_name=f"Operation {ProcessOperationType.SUBMIT.value} {target_operation_step.id} "
                    f"for process {process.id} of action {action.display_name}",
                    operation_result="success",
                    operation_type=AuditLogOperationType.UPDATE,
                    **self.prepare_audit_object_arguments(expected_object=obj, is_deleted=False),
                    user__username="admin",
                )
                ConcernItem.objects.all().delete()

    def test_audit_record_process_create(self):
        with self.subTest(f"create process for {self.cluster_1} (access denied)"):
            self.client.login(**self.test_user_credentials)
            action = self.get_object_action_with_process(self.cluster_1)
            response = self.client.v2[self.cluster_1, "actions", action.pk, "processes"].post(data={})

            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
            self.check_last_audit_record(
                operation_name=f"Process of action {action.display_name} created",
                operation_result="denied",
                operation_type=AuditLogOperationType.CREATE,
                **self.prepare_audit_object_arguments(expected_object=self.cluster_1, is_deleted=False),
                user__username=self.test_user_credentials["username"],
            )

        with self.subTest(f"create process for {self.cluster_1} (not found)"):
            self.client.login(username="admin", password="admin")
            response = self.client.v2[self.cluster_1, "actions", 999, "processes"].post(data={})

            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
            self.check_last_audit_record(
                operation_name="Process of action created",
                operation_result="fail",
                operation_type=AuditLogOperationType.CREATE,
                **self.prepare_audit_object_arguments(expected_object=self.cluster_1, is_deleted=False),
                user__username="admin",
            )

        with self.subTest(f"create process for {self.cluster_1} (failed)"):
            self.client.login(username="admin", password="admin")
            action = Action.objects.get(name="regular_action", prototype=self.cluster_1.prototype)
            response = self.client.v2[self.cluster_1, "actions", action.pk, "processes"].post(data={})

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.check_last_audit_record(
                operation_name=f"Process of action {action.display_name} created",
                operation_result="fail",
                operation_type=AuditLogOperationType.CREATE,
                **self.prepare_audit_object_arguments(expected_object=self.cluster_1, is_deleted=False),
                user__username="admin",
            )

        for obj in (self.cluster_1, self.service_1, self.component_1):
            with self.subTest(f"create process for {obj} (success)"):
                self.client.login(username="admin", password="admin")
                action = self.get_object_action_with_process(obj)
                response = self.client.v2[obj, "actions", action.pk, "processes"].post(data={})

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.check_last_audit_record(
                    operation_name=f"Process of action {action.display_name} created",
                    operation_result="success",
                    operation_type=AuditLogOperationType.CREATE,
                    **self.prepare_audit_object_arguments(expected_object=obj, is_deleted=False),
                    user__username="admin",
                )
