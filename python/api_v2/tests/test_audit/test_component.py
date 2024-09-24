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


from cm.models import Action, Cluster, MaintenanceMode, Service, ServiceComponent
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestComponentAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1)
        self.service_1 = Service.objects.get(cluster=self.cluster_1, prototype__name="service_1")
        self.component_1 = ServiceComponent.objects.get(prototype__name="component_1", service=self.service_1)
        self.component_action = Action.objects.get(name="action_1_comp_1", prototype=self.component_1.prototype)
        self.config_post_data = {
            "config": {
                "group": {"file": "new content"},
                "activatable_group": {"secretfile": "new content"},
                "secrettext": "new secrettext",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }

    def test_run_action_success(self):
        response = self.client.v2[self.component_1, "actions", self.component_action.pk, "run"].post()
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name=f"{self.component_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_run_action_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.component_1, role_name="View component configurations"):
            response = self.client.v2[self.component_1, "actions", self.component_action, "run"].post()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.component_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_run_action_fail(self):
        response = self.client.v2[self.component_1, "actions", self.get_non_existent_pk(model=Action), "run"].post()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="action launched",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_update_config_success(self):
        response = self.client.v2[self.component_1, "configs"].post(data=self.config_post_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="Component configuration updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_update_config_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.v2[self.component_1, "configs"].post(data=self.config_post_data)
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Component configuration updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_update_config_only_view_denied(self):
        self.client.login(**self.test_user_credentials)

        with (
            self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"),
            self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"),
            self.grant_permissions(to=self.test_user, on=self.component_1, role_name="View component configurations"),
        ):
            response = self.client.v2[self.component_1, "configs"].post(data=self.config_post_data)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Component configuration updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_update_config_wrong_data_fail(self):
        response = self.client.v2[self.component_1, "configs"].post(data={"wrong": ["d", "a", "t", "a"]})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Component configuration updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_update_config_not_exists_fail(self):
        response = self.client.v2[
            self.service_1, "components", self.get_non_existent_pk(model=ServiceComponent), "configs"
        ].post(
            data=self.config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Component configuration updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_change_mm_success(self):
        response = self.client.v2[self.component_1, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name="Component updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            object_changes={"current": {"maintenance_mode": "on"}, "previous": {"maintenance_mode": "off"}},
            user__username="admin",
        )

    def test_change_mm_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.v2[self.component_1, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Component updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_change_mm_denied(self):
        self.client.login(**self.test_user_credentials)

        with (
            self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"),
            self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"),
            self.grant_permissions(to=self.test_user, on=self.component_1, role_name="View component configurations"),
        ):
            response = self.client.v2[self.component_1, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Component updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_change_mm_incorrect_body_fail(self):
        response = self.client.v2[self.component_1, "maintenance-mode"].post(data={"maintenanceMode": "cough"})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Component updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_change_mm_from_changing_state_fail(self):
        self.component_1.maintenance_mode = MaintenanceMode.CHANGING
        self.component_1.save(update_fields=["_maintenance_mode"])

        response = self.client.v2[self.component_1, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_record(
            operation_name="Component updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(self.component_1),
            user__username="admin",
        )

    def test_change_mm_not_found_fail(self):
        audit_object_kwargs = self.prepare_audit_object_arguments(expected_object=self.component_1)
        audit_object_none_kwargs = self.prepare_audit_object_arguments(expected_object=None)
        endpoints = {
            "absent_cluster": (
                self.client.v2
                / "clusters"
                / self.get_non_existent_pk(model=Cluster)
                / "services"
                / self.service_1.pk
                / "components"
                / self.component_1.pk
                / "maintenance-mode",
                audit_object_kwargs,
            ),
            "absent_service": (
                self.client.v2
                / "clusters"
                / self.cluster_1.pk
                / "services"
                / self.get_non_existent_pk(model=Service)
                / "components"
                / self.component_1.pk
                / "maintenance-mode",
                audit_object_kwargs,
            ),
            "absent_component": (
                self.client.v2
                / "clusters"
                / self.cluster_1.pk
                / "services"
                / self.service_1.pk
                / "components"
                / self.get_non_existent_pk(model=ServiceComponent)
                / "maintenance-mode",
                audit_object_none_kwargs,
            ),
        }

        for name, data in endpoints.items():
            endpoint, object_kwargs = data

            with self.subTest(name):
                response = endpoint.post(data={"maintenanceMode": "on"})

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
                self.check_last_audit_record(
                    operation_name="Component updated",
                    operation_type="update",
                    operation_result="fail",
                    **object_kwargs,
                    user__username="admin",
                )
