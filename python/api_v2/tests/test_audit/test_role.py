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
from rbac.models import Role
from rbac.services.role import role_create
from rbac.services.user import create_user
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


class TestRoleAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        self.role_create_data = {
            "displayName": "Custom `view cluster configurations` role",
            "children": [Role.objects.get(name="View cluster configurations").pk],
        }

        self.custom_role = role_create(
            display_name="Custom `view service configurations` role",
            child=[Role.objects.get(name="View service configurations")],
        )

    def test_role_create_success(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:role-list"), data=self.role_create_data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_log(
            operation_name="Role created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=response.json()["id"],
            audit_object__object_name=self.role_create_data["displayName"],
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_role_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:rbac:role-list"), data=self.role_create_data)

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Role created",
            operation_type="create",
            operation_result="denied",
            audit_object__isnull=True,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_role_create_wrong_data_fail(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:role-list"), data={"displayName": "Some role"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_log(
            operation_name="Role created",
            operation_type="create",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_role_update_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk}),
            data=self.role_create_data,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name="Role updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.custom_role.pk,
            audit_object__object_name=self.custom_role.name,
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={
                "current": {
                    "display_name": "Custom `view cluster configurations` role",
                    "child": ["View cluster configurations"],
                },
                "previous": {
                    "display_name": "Custom `view service configurations` role",
                    "child": ["View service configurations"],
                },
            },
            user__username="admin",
        )

    def test_role_update_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View roles"):
            response = self.client.patch(
                path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk}),
                data=self.role_create_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Role updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.custom_role.pk,
            audit_object__object_name=self.custom_role.name,
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_role_update_duplicate_name_fail(self):
        role_create(display_name="Custom role name", child=[Role.objects.get(name="View cluster configurations")])

        response = self.client.patch(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk}),
            data={"displayName": "Custom role name"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.check_last_audit_log(
            operation_name="Role updated",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.custom_role.pk,
            audit_object__object_name=self.custom_role.name,
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_role_delete_success(self):
        AuditObject.objects.get_or_create(
            object_id=self.custom_role.pk,
            object_name=self.custom_role.name,
            object_type="role",
            is_deleted=False,
        )
        expected_audit_object_kwargs = {
            "audit_object__object_id": self.custom_role.pk,
            "audit_object__object_name": self.custom_role.name,
            "audit_object__object_type": "role",
            "audit_object__is_deleted": True,
        }
        response = self.client.delete(path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk}))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.check_last_audit_log(
            operation_name="Role deleted",
            operation_type="delete",
            operation_result="success",
            **expected_audit_object_kwargs,
            object_changes={},
            user__username="admin",
        )

    def test_role_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View roles"):
            response = self.client.delete(
                path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk})
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Role deleted",
            operation_type="delete",
            operation_result="denied",
            audit_object__object_id=self.custom_role.pk,
            audit_object__object_name=self.custom_role.name,
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_role_delete_not_exists_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.get_non_existent_pk(model=Role)})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="Role deleted",
            operation_type="delete",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )
