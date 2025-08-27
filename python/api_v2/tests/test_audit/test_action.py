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

from audit.models import AuditLogOperationType
from cm.models import ADCM, Action, Cluster, Component, Service
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestActionProcessAudit(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        wizard_cluster_bundle = self.test_bundles_dir / "wizard_action"
        self.bundle_1 = self.add_bundle(source_dir=wizard_cluster_bundle)
        self.cluster_1 = self.add_cluster(bundle=self.bundle_1, name="cluster_1", description="cluster_1")

        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster_1).first()
        self.component_1 = Component.objects.filter(service=self.service_1).first()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def get_object_wizard_action(self, obj: Cluster | Service | Component) -> Action:
        return Action.objects.get(name="wizard_jinja", prototype=obj.prototype)

    def test_audit_record_process_create(self):
        with self.subTest(f"create process for {self.cluster_1} (access denied)"):
            self.client.login(**self.test_user_credentials)
            action = self.get_object_wizard_action(self.cluster_1)
            response = self.client.v2[self.cluster_1, "actions", action.pk, "processes"].post(data={})

            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
            self.check_last_audit_record(
                operation_name=f"Process of action {action.display_name} created",
                operation_result="fail",
                operation_type=AuditLogOperationType.CREATE,
                **self.prepare_audit_object_arguments(expected_object=self.cluster_1, is_deleted=False),
                user__username=self.test_user_credentials["username"],
            )

        with self.subTest(f"create process for {self.cluster_1} (not found)"):
            self.client.login(username="admin", password="admin")
            action = self.get_object_wizard_action(self.cluster_1)
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
            action = Action.objects.filter(prototype=ADCM.objects.first().prototype).first()
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
                action = self.get_object_wizard_action(obj)
                response = self.client.v2[obj, "actions", action.pk, "processes"].post(data={})

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                self.check_last_audit_record(
                    operation_name=f"Process of action {action.display_name} created",
                    operation_result="success",
                    operation_type=AuditLogOperationType.CREATE,
                    **self.prepare_audit_object_arguments(expected_object=obj, is_deleted=False),
                    user__username="admin",
                )
