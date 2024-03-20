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
from rbac.models import Group
from rbac.services.group import create as create_group
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


class TestGroupAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.blocked_user = self.create_user({"username": "blocked_user", "password": "blocked_user_pswd"})
        self.blocked_user.blocked_at = timezone.now()
        self.blocked_user.save(update_fields=["blocked_at"])

        self.group_update_data = {
            "displayName": "new display name",
            "description": "new description",
            "users": [self.blocked_user.pk],
        }
        self.group = create_group(name_to_display="Some group")

    def test_group_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:group-list"),
            data={"displayName": "New test group"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_record(
            operation_name="Group created",
            operation_type="create",
            operation_result="success",
            **self.prepare_audit_object_arguments(Group.objects.get(pk=response.json()["id"])),
            user__username="admin",
        )

    def test_group_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:rbac:group-list"),
            data={"displayName": "New test group"},
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_record(
            operation_name="Group created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username=self.test_user.username,
        )

    def test_group_create_wrong_data_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:group-list"),
            data={"description": "dscr"},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_record(
            operation_name="Group created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_group_update_success(self):
        expected_object_changes = {
            "current": {
                "description": "new description",
                "name": "new display name",
                "user": [self.blocked_user.username],
            },
            "previous": {"description": "", "name": "Some group", "user": []},
        }

        response = self.client.patch(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
            data=self.group_update_data,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        self.group.refresh_from_db()

        last_audit_log = self.check_last_audit_record(
            operation_name="Group updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.group),
            user__username="admin",
            expect_object_changes_=False,
        )
        self.assertDictEqual(last_audit_log.object_changes, expected_object_changes)

    def test_group_update_one_field_success(self):
        expected_object_changes = {
            "current": {
                "name": "new display name",
            },
            "previous": {"name": "Some group"},
        }

        response = self.client.patch(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
            data={"displayName": "new display name"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        self.group.refresh_from_db()

        last_audit_log = self.check_last_audit_record(
            operation_name="Group updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.group),
            user__username="admin",
            expect_object_changes_=False,
        )
        self.assertDictEqual(last_audit_log.object_changes, expected_object_changes)

    def test_group_update_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.patch(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
            data=self.group_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_record(
            operation_name="Group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.group),
            user__username=self.test_user.username,
        )

    def test_group_update_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View group"):
            response = self.client.patch(
                path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
                data=self.group_update_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_record(
            operation_name="Group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.group),
            user__username=self.test_user.username,
        )

    def test_group_update_incorrect_data_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
            data={"displayName": []},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_record(
            operation_name="Group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.group),
            user__username="admin",
        )

    def test_group_update_not_exists_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.get_non_existent_pk(model=Group)}),
            data=self.group_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_record(
            operation_name="Group updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_group_delete_success(self):
        # audit object should exist before successful DELETE request
        # to have `is_deleted` updated
        # for now we've agreed that's ok tradeoff
        AuditObject.objects.get_or_create(
            object_id=self.group.pk,
            object_name=self.group.name,
            object_type="group",
            is_deleted=False,
        )

        response = self.client.delete(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name="Group deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.group, is_deleted=True),
            user__username="admin",
        )

    def test_group_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.delete(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_record(
            operation_name="Group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.group),
            user__username=self.test_user.username,
        )

    def test_group_delete_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View group"):
            response = self.client.delete(
                path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_record(
            operation_name="Group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.group),
            user__username=self.test_user.username,
        )

    def test_group_delete_not_exists_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.get_non_existent_pk(model=Group)}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_record(
            operation_name="Group deleted",
            operation_type="delete",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )
