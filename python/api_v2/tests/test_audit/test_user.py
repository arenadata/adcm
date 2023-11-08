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
from django.utils import timezone
from rbac.models import User
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


class TestUserAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        self.blocked_user = create_user(username="blocked_user", password="blocked_user_pswd")
        self.blocked_user.blocked_at = timezone.now()
        self.blocked_user.save(update_fields=["blocked_at"])

        self.user_create_data = {
            "username": "newuser",
            "password": "newusernewuser",
            "firstName": "newuser",
            "lastName": "newuser",
            "email": "newuser@newuser.newuser",
            "isSuperUser": False,
        }
        self.user_update_data = {"lastName": "new_last_name"}

    def test_user_create_success(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:user-list"), data=self.user_create_data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_log(
            operation_name="User created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=response.json()["id"],
            audit_object__object_name=self.user_create_data["username"],
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_user_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:rbac:user-list"), data={"wrong": "data"})

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="User created",
            operation_type="create",
            operation_result="denied",
            audit_object__isnull=True,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_create_wrong_data_fail(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:user-list"), data={"wrong": "data"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_log(
            operation_name="User created",
            operation_type="create",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_user_update_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.test_user.pk}), data=self.user_update_data
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name="User updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.test_user.pk,
            audit_object__object_name=self.test_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={"current": {"last_name": "new_last_name"}, "previous": {"last_name": ""}},
            user__username="admin",
        )

    def test_user_update_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response = self.client.patch(
                path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk}),
                data=self.user_update_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="User updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_update_no_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk}),
            data=self.user_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="User updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_update_not_exists_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.get_non_existent_pk(model=User)}),
            data=self.user_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="User updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_user_delete_success(self):
        AuditObject.objects.get_or_create(
            object_id=self.blocked_user.pk,
            object_name=self.blocked_user.name,
            object_type="user",
            is_deleted=False,
        )
        expected_audit_object_kwargs = {
            "audit_object__object_id": self.blocked_user.pk,
            "audit_object__object_name": self.blocked_user.name,
            "audit_object__object_type": "user",
            "audit_object__is_deleted": True,
        }

        response = self.client.delete(path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk}))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.check_last_audit_log(
            operation_name="User deleted",
            operation_type="delete",
            operation_result="success",
            **expected_audit_object_kwargs,
            object_changes={},
            user__username="admin",
        )

    def test_user_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response = self.client.delete(
                path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk})
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="User deleted",
            operation_type="delete",
            operation_result="denied",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_delete_non_existent_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.get_non_existent_pk(model=User)})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="User deleted",
            operation_type="delete",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_user_unblock_success(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": self.blocked_user.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name=f"{self.blocked_user.username} user unblocked",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_user_unblock_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response = self.client.post(
                path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": self.blocked_user.pk})
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name=f"{self.blocked_user.username} user unblocked",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_unblock_not_exists_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": self.get_non_existent_pk(model=User)})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="user unblocked",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )
