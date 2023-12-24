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
from rbac.models import Policy, Role
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
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


class TestPolicyAudit(BaseAPITestCase):  # pylint: disable=too-many-instance-attributes
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        custom_role = role_create(
            display_name="Custom role name",
            child=[Role.objects.get(name="View cluster configurations")],
        )
        self.another_role = role_create(
            display_name="Another custom role name",
            child=[Role.objects.get(name="Edit cluster configurations")],
        )
        self.group = create_group(name_to_display="Some group")
        self.another_group = create_group(name_to_display="Other group")
        self.another_group_2 = create_group(name_to_display="Other group 2")
        self.policy_create_data = {
            "name": "New Policy",
            "role": {"id": custom_role.pk},
            "objects": [{"id": self.cluster_1.pk, "type": "cluster"}],
            "groups": [self.group.pk],
        }
        self.policy_update_data = {"name": "Updated name"}
        self.policy = policy_create(
            name="Test policy",
            role=Role.objects.get(name="View provider configurations"),
            group=[self.another_group],
            object=[self.provider],
        )
        self.another_policy = policy_create(
            name="Test policy 2",
            role=Role.objects.get(name="View cluster configurations"),
            group=[self.group],
            object=[self.cluster_1],
        )

    def test_policy_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:policy-list"),
            data=self.policy_create_data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_record(
            operation_name="Policy created",
            operation_type="create",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=Policy.objects.get(pk=response.json()["id"])),
            user__username="admin",
        )

    def test_policy_create_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View policy"):
            response = self.client.post(
                path=reverse(viewname="v2:rbac:policy-list"),
                data=self.policy_create_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_record(
            operation_name="Policy created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username=self.test_user.username,
        )

    def test_policy_create_wrong_data_fail(self):
        wrong_data = self.policy_create_data.copy()
        wrong_data["objects"] = [{"id": self.provider.pk, "type": "provider"}]

        response = self.client.post(
            path=reverse(viewname="v2:rbac:policy-list"),
            data=wrong_data,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.check_last_audit_record(
            operation_name="Policy created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_policy_edit_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data=self.policy_update_data,
        )

        self.policy.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_record(
            operation_name="Policy updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.policy),
            object_changes={"current": {"name": "Updated name"}, "previous": {"name": "Test policy"}},
            user__username="admin",
        )

    def test_policy_all_fields_edit_success(self):
        policy_update_data = {
            "name": "Updated name",
            "description": "new description",
            "groups": [self.another_group.pk, self.another_group_2.pk],
            "role": {"id": self.another_role.pk},
            "object": [{"name": self.cluster_2.name, "type": self.cluster_2.prototype.type, "id": self.cluster_2.pk}],
        }
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.another_policy.pk}),
            data=policy_update_data,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.another_policy.refresh_from_db()

        expected_object_changes = {
            "current": {
                "name": "Updated name",
                "description": "new description",
                "role": "Another custom role name",
                "group": ["Other group [local]", "Other group 2 [local]"],
            },
            "previous": {
                "name": "Test policy 2",
                "description": "",
                "role": "View cluster configurations",
                "group": ["Some group [local]"],
            },
        }
        last_record = self.check_last_audit_record(
            operation_name="Policy updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.another_policy),
            user__username="admin",
            expect_object_changes_=False,
        )
        self.assertDictEqual(expected_object_changes, last_record.object_changes)

    def test_policy_edit_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data=self.policy_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_record(
            operation_name="Policy updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.policy),
            user__username=self.test_user.username,
        )

    def test_policy_edit_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View policy"):
            response = self.client.patch(
                path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}),
                data=self.policy_update_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_record(
            operation_name="Policy updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.policy),
            user__username=self.test_user.username,
        )

    def test_policy_edit_incorrect_data_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data={"name": ""},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_record(
            operation_name="Policy updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.policy),
            user__username="admin",
        )

    def test_policy_edit_not_exists_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.get_non_existent_pk(model=Policy)}),
            data=self.policy_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_record(
            operation_name="Policy updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_policy_delete_success(self):
        # audit object should exist before successful DELETE request
        # to have `is_deleted` updated
        # for now we've agreed that's ok tradeoff
        AuditObject.objects.get_or_create(
            object_id=self.policy.pk,
            object_name=self.policy.name,
            object_type="policy",
            is_deleted=False,
        )

        response = self.client.delete(path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}))
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name="Policy deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.policy, is_deleted=True),
            user__username="admin",
        )

    def test_policy_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.delete(path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}))
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Policy deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.policy),
            user__username=self.test_user.username,
        )

    def test_policy_delete_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View policy"):
            response = self.client.delete(path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}))

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_record(
            operation_name="Policy deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.policy),
            user__username=self.test_user.username,
        )

    def test_policy_delete_not_exists_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.get_non_existent_pk(model=Policy)})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_record(
            operation_name="Policy deleted",
            operation_type="delete",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )
