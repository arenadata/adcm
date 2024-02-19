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

from audit.models import AuditObject
from django.utils import timezone
from rbac.models import User
from rbac.services.group import create as create_group
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

from api_v2.tests.base import BaseAPITestCase


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

        self.group = create_group(name_to_display="Some group")

    def test_user_create_success(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:user-list"), data=self.user_create_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="User created",
            operation_type="create",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=User.objects.get(pk=response.json()["id"])),
            user__username="admin",
        )

    def test_user_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:rbac:user-list"), data={"wrong": "data"})

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_record(
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

        self.check_last_audit_record(
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

        self.check_last_audit_record(
            operation_name="User updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.test_user),
            object_changes={"current": {"last_name": "new_last_name"}, "previous": {"last_name": ""}},
            user__username="admin",
        )

    def test_user_update_all_fields_success(self):
        user_update_data = {
            "first_name": "new_first_name",
            "lastName": "new_last_name",
            "email": "email@new.mail",
            "is_superuser": True,
            "password": "new_password1",
            "groups": [self.group.pk],
        }
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.test_user.pk}), data=user_update_data
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_object_changes = {
            "current": {
                "email": "email@new.mail",
                "first_name": "new_first_name",
                "last_name": "new_last_name",
                "password": "******",
                "group": ["Some group [local]"],
            },
            "previous": {
                "email": "",
                "first_name": "",
                "last_name": "",
                "password": "******",
                "group": [],
            },
        }

        last_record = self.check_last_audit_record(
            operation_name="User updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.test_user),
            user__username="admin",
            expect_object_changes_=False,
        )
        self.assertDictEqual(expected_object_changes, last_record.object_changes)

    def test_user_update_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response = self.client.patch(
                path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk}),
                data=self.user_update_data,
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="User updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username=self.test_user.username,
        )

    def test_user_update_no_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk}),
            data=self.user_update_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="User updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username=self.test_user.username,
        )

    def test_user_update_incorrect_data_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.test_user.pk}),
            data={"email": "s"},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="User updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.test_user),
            user__username="admin",
        )

    def test_user_update_not_exists_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.get_non_existent_pk(model=User)}),
            data=self.user_update_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="User updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_user_delete_success(self):
        # audit object should exist before successful DELETE request
        # to have `is_deleted` updated
        # for now we've agreed that's ok tradeoff
        AuditObject.objects.get_or_create(
            object_id=self.blocked_user.pk,
            object_name=self.blocked_user.name,
            object_type="user",
            is_deleted=False,
        )

        response = self.client.delete(path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk}))
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name="User deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user, is_deleted=True),
            user__username="admin",
        )

    def test_user_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.delete(path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk}))
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="User deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username=self.test_user.username,
        )

    def test_user_delete_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response = self.client.delete(
                path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk})
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="User deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username=self.test_user.username,
        )

    def test_user_delete_non_existent_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.get_non_existent_pk(model=User)})
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
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

        self.check_last_audit_record(
            operation_name=f"{self.blocked_user.username} user unblocked",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username="admin",
        )

    def test_user_unblock_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": self.blocked_user.pk}))
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.blocked_user.username} user unblocked",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username=self.test_user.username,
        )

    def test_user_unblock_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response = self.client.post(
                path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": self.blocked_user.pk})
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.blocked_user.username} user unblocked",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username=self.test_user.username,
        )

    def test_user_unblock_not_exists_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": self.get_non_existent_pk(model=User)})
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="user unblocked",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_user_block_success(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:user-block", kwargs={"pk": self.blocked_user.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name=f"{self.blocked_user.username} user blocked",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username="admin",
        )

    def test_user_block_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:rbac:user-block", kwargs={"pk": self.blocked_user.pk}))
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.blocked_user.username} user blocked",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username=self.test_user.username,
        )

    def test_user_block_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response = self.client.post(
                path=reverse(viewname="v2:rbac:user-block", kwargs={"pk": self.blocked_user.pk})
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.blocked_user.username} user blocked",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.blocked_user),
            user__username=self.test_user.username,
        )

    def test_user_block_not_exists_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:user-block", kwargs={"pk": self.get_non_existent_pk(model=User)})
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="user blocked",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )
