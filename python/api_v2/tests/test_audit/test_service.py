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

from cm.models import Action, Cluster, MaintenanceMode, ObjectType, Service
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestServiceAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.config_post_data = {
            "config": {
                "group": {"password": "newpassword"},
                "activatable_group": {"text": "new text"},
                "string": "new string",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }

        self.export_service = self.add_services_to_cluster(service_names=["service"], cluster=self.cluster_2).get()
        self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1)
        self.service_1 = Service.objects.get(cluster=self.cluster_1, prototype__name="service_1")

        self.service_action = Action.objects.get(name="action", prototype=self.service_1.prototype)

    def test_update_config_success(self):
        response = self.client.v2[self.service_1, "configs"].post(data=self.config_post_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="Service configuration updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_update_config_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.v2[self.service_1, "configs"].post(data=self.config_post_data)
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Service configuration updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_update_config_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"):
            response = self.client.v2[self.service_1, "configs"].post(data=self.config_post_data)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Service configuration updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_update_config_wrong_data_fail(self):
        response = self.client.v2[self.service_1, "configs"].post(data={"wrong": ["d", "a", "t", "a"]})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Service configuration updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username="admin",
        )

    def test_update_config_not_exists_fail(self):
        response = self.client.v2[self.cluster_1, "services", self.get_non_existent_pk(model=Service), "configs"].post(
            data=self.config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Service configuration updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_change_mm_success(self):
        response = self.client.v2[self.service_1, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name="Service updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(self.service_1),
            object_changes={"current": {"maintenance_mode": "on"}, "previous": {"maintenance_mode": "off"}},
            user__username="admin",
        )

    def test_change_mm_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.v2[self.service_1, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Service updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username=self.test_user.username,
        )

    def test_change_mm_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"):
            response = self.client.v2[self.service_1, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Service updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username=self.test_user.username,
        )

    def test_change_mm_incorrect_data_fail(self):
        response = self.client.v2[self.service_1, "maintenance-mode"].post(data={})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Service updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username="admin",
        )

    def test_change_mm_from_changing_state_fail(self):
        self.service_1.maintenance_mode = MaintenanceMode.CHANGING
        self.service_1.save(update_fields=["_maintenance_mode"])

        response = self.client.v2[self.service_1, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_record(
            operation_name="Service updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username="admin",
        )

    def test_change_mm_not_exist_fail(self):
        endpoints = {
            "absent_cluster": (
                self.client.v2
                / "clusters"
                / self.get_non_existent_pk(model=Cluster)
                / "services"
                / self.service_1.pk
                / "maintenance-mode",
                self.prepare_audit_object_arguments(expected_object=self.service_1),
            ),
            "absent_service": (
                self.client.v2
                / "clusters"
                / self.cluster_1.pk
                / "services"
                / self.get_non_existent_pk(model=Service)
                / "maintenance-mode",
                self.prepare_audit_object_arguments(expected_object=None),
            ),
        }

        for name, data in endpoints.items():
            endpoint, object_kwargs = data

            with self.subTest(name):
                response = endpoint.post(data={"maintenanceMode": "on"})

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
                self.check_last_audit_record(
                    operation_name="Service updated",
                    operation_type="update",
                    operation_result="fail",
                    **object_kwargs,
                    user__username="admin",
                )

    def test_run_action_success(self):
        response = self.client.v2[self.service_1, "actions", self.service_action, "run"].post()
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name=f"{self.service_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username="admin",
        )

    def test_run_action_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"):
            response = self.client.v2[self.service_1, "actions", self.service_action, "run"].post()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.service_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username=self.test_user.username,
        )

    def test_run_action_not_found_fail(self):
        response = self.client.v2[self.service_1, "actions", self.get_non_existent_pk(model=Action), "run"].post()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="action launched",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username="admin",
        )

    def test_create_import_success(self):
        response = self.client.v2[self.service_1, "imports"].post(
            data=[{"source": {"id": self.export_service.pk, "type": ObjectType.SERVICE}}],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="Service import updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username="admin",
        )

    def test_create_import_no_perm_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.v2[self.service_1, "imports"].post(
            data=[{"source": {"id": self.export_service.pk, "type": ObjectType.SERVICE}}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Service import updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username=self.test_user.username,
        )

    def test_create_import_view_perm_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(
            to=self.test_user, on=self.service_1, role_name="View service configurations"
        ), self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
            response = self.client.v2[self.service_1, "imports"].post(
                data=[{"source": {"id": self.export_service.pk, "type": ObjectType.SERVICE}}],
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Service import updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username=self.test_user.username,
        )

    def test_create_import_incorrect_data_fail(self):
        response = self.client.v2[self.service_1, "imports"].post(
            data=[{"source": {"id": self.export_service.pk, "type": "cool"}}],
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Service import updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(self.service_1),
            user__username="admin",
        )

    def test_create_import_not_found_fail(self):
        response = self.client.v2[self.cluster_1, "services", self.get_non_existent_pk(model=Service), "imports"].post(
            data=[{"source": {"id": self.export_service.pk, "type": ObjectType.SERVICE}}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Service import updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_remove_service_success(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Remove service"):
            response = self.client.v2[self.service_1].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_remove_service_not_found_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.v2[self.service_1].delete()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_remove_service_view_perm_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"):
            response = self.client.v2[self.service_1].delete()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(self.cluster_1),
            user__username=self.test_user.username,
        )
