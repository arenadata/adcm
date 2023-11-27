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

from api_v2.tests.base import BaseAPITestCase
from audit.models import AuditObject
from cm.models import Host, ObjectType, Prototype
from rbac.services.user import create_user
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)


class TestHostAudit(BaseAPITestCase):  # pylint:disable=too-many-public-methods
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        self.prototype = Prototype.objects.get(bundle=self.bundle_1, type=ObjectType.CLUSTER)
        self.host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_2")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)

    def test_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={
                "hostproviderId": self.provider.pk,
                "name": "new-test-host",
            },
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="Host created",
            operation_type="create",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=Host.objects.get(pk=response.json()["id"])),
            user__username="admin",
        )

    def test_create_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={
                "name": "new-test-host",
            },
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Host created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_create_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={
                "hostproviderId": self.provider.pk,
                "name": "new-test-host",
            },
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Host created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username=self.test_user.username,
        )

    def test_update_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
            data={"name": "new.name"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.host_2.refresh_from_db()

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.host_2),
            user__username="admin",
        )

    def test_update_incorrect_data_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
            data={"name": "a"},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.host_2),
            user__username="admin",
        )

    def test_update_not_found_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": 1000}),
            data={"name": "new.name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_update_view_config_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.host_2], role_name="View host configurations"):
            response = self.client.patch(
                path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
                data={"name": "new.name"},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_2),
            user__username=self.test_user.username,
        )

    def test_update_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
            data={"name": "new.name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_2),
            user__username=self.test_user.username,
        )

    def test_delete_success(self):
        # audit object should exist before successful DELETE request
        # to have `is_deleted` updated
        # for now we've agreed that's ok tradeoff
        AuditObject.objects.get_or_create(
            object_id=self.host_2.pk,
            object_name=self.host_2.name,
            object_type="host",
            is_deleted=False,
        )

        response = self.client.delete(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.check_last_audit_record(
            operation_name="Host deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.host_2, is_deleted=True),
            user__username="admin",
        )

    def test_delete_not_found_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": 1000}),
            data={"name": "new.name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host deleted",
            operation_type="delete",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_delete_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.host_2], role_name="View host configurations"):
            response = self.client.delete(
                path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Host deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_2),
            user__username=self.test_user.username,
        )

    def test_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_2),
            user__username=self.test_user.username,
        )

    def test_remove_from_cluster_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name=f"{self.host_1.fqdn} host removed",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
        )

    def test_remove_from_cluster_not_found_cluster_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:host-cluster-detail", kwargs={"cluster_pk": 100, "pk": self.host_2.pk}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="test_host_2 host removed",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
        )

    def test_remove_from_cluster_not_found_host_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": 1000}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="host removed",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
        )

    def test_remove_from_cluster_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.cluster_1], role_name="View cluster configurations"):
            response = self.client.delete(
                path=reverse(
                    viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk}
                ),
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.host_1.fqdn} host removed",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_remove_from_cluster_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.host_1.fqdn} host removed",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_switch_maintenance_mode_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-maintenance-mode",
                kwargs={"pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="success",
            object_changes={"current": {"maintenance_mode": "on"}, "previous": {"maintenance_mode": "off"}},
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
        )

    def test_switch_maintenance_mode_incorrect_body_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-maintenance-mode",
                kwargs={"pk": self.host_1.pk},
            ),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
        )

    def test_switch_maintenance_mode_not_found_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-maintenance-mode",
                kwargs={"pk": 1000},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_switch_maintenance_mode_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.host_1], role_name="View host configurations"):
            response = self.client.post(
                path=reverse(
                    viewname="v2:host-maintenance-mode",
                    kwargs={"pk": self.host_1.pk},
                ),
                data={"maintenanceMode": "on"},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username=self.test_user.username,
        )

    def test_switch_maintenance_mode_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:host-maintenance-mode",
                kwargs={"pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username=self.test_user.username,
        )

    def test_switch_maintenance_mode_cluster_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            object_changes={"current": {"maintenance_mode": "on"}, "previous": {"maintenance_mode": "off"}},
        )

    def test_switch_maintenance_mode_cluster_incorrect_body_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
        )

    def test_switch_maintenance_mode_cluster_not_found_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": 1000},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
        )

    def test_switch_maintenance_mode_cluster_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username=self.test_user.username,
        )

    def test_update_host_config_success(self):
        data = {
            "config": {
                "activatable_group": {"option": "string2"},
                "group": {"list": ["value1", "value2", "value3", "value4"]},
                "structure": [
                    {"integer": 1, "string": "string1"},
                    {"integer": 2, "string": "string2"},
                    {"integer": 3, "string": "string3"},
                ],
                "variant": "value2",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.host_1.pk}),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="Host configuration updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
        )

    def test_update_host_config_incorrect_data_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.host_1.pk}),
            data={"config": {}, "adcmMeta": {"/activatable_group": {"isActive": True}}},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Host configuration updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
        )

    def test_update_host_config_not_found_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": 1000}),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host configuration updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_update_host_config_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.host_1], role_name="View host configurations"):
            response = self.client.post(
                path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.host_1.pk}),
                data={},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Host configuration updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username=self.test_user.username,
        )

    def test_update_host_config_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.host_1.pk}),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host configuration updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username=self.test_user.username,
        )
