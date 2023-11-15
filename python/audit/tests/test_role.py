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

from datetime import datetime

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from django.urls import reverse
from rbac.models import Role, RoleTypes, User
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestRoleAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.role_display_name = "test_role"
        self.child = Role.objects.create(
            name="test_child_role",
            display_name="test_child_role",
            type=RoleTypes.BUSINESS,
        )
        self.role = Role.objects.create(name="test_role_2", built_in=False)
        self.list_name = "v1:rbac:role-list"
        self.detail_name = "v1:rbac:role-detail"
        self.role_created_str = "Role created"
        self.role_updated_str = "Role updated"

    def check_log(
        self,
        log: AuditLog,
        obj: Role | None,
        operation_name: str,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
        object_changes: dict | None = None,
        object_is_deleted: bool = False,
    ) -> None:
        if obj:
            self.assertEqual(log.audit_object.object_id, obj.pk)
            self.assertEqual(log.audit_object.object_name, obj.name)
            self.assertEqual(log.audit_object.object_type, AuditObjectType.ROLE)
            self.assertEqual(log.audit_object.is_deleted, object_is_deleted)
        else:
            self.assertFalse(log.audit_object)

        if object_changes is None:
            object_changes = {}

        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, user.username)
        self.assertEqual(log.object_changes, object_changes)

    def check_log_update(
        self,
        log: AuditLog,
        obj: Role,
        operation_result: AuditLogOperationResult,
        user: User,
        object_changes: dict | None = None,
    ) -> None:
        if object_changes is None:
            object_changes = {}

        return self.check_log(
            log=log,
            obj=obj,
            operation_name=self.role_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=operation_result,
            user=user,
            object_changes=object_changes,
        )

    def test_create(self):
        response: Response = self.client.post(
            path=reverse(viewname=self.list_name),
            data={
                "display_name": self.role_display_name,
                "child": [{"id": self.child.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        role = Role.objects.get(pk=response.data["id"])

        self.check_log(
            log=log,
            obj=role,
            operation_name=self.role_created_str,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

        self.client.post(
            path=reverse(viewname=self.list_name),
            data={
                "display_name": self.role_display_name,
                "child": [{"id": self.child.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=None,
            operation_name=self.role_created_str,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.test_user,
        )

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname=self.list_name),
                data={
                    "display_name": self.role_display_name,
                    "child": [{"id": self.child.pk}],
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=None,
            operation_name=self.role_created_str,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_delete(self):
        self.client.delete(
            path=reverse(viewname=self.detail_name, kwargs={"pk": self.role.pk}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.role,
            operation_name="Role deleted",
            operation_type=AuditLogOperationType.DELETE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(viewname=self.detail_name, kwargs={"pk": self.role.pk}),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.role,
            operation_name="Role deleted",
            operation_type=AuditLogOperationType.DELETE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_put(self):
        new_display_name = "new_display_name"
        prev_display_name = self.role.display_name
        self.client.put(
            path=reverse(viewname=self.detail_name, kwargs={"pk": self.role.pk}),
            data={
                "display_name": new_display_name,
                "child": [{"id": self.child.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_update(
            log=log,
            obj=self.role,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            object_changes={
                "current": {"display_name": new_display_name, "child": [self.child.display_name]},
                "previous": {"display_name": prev_display_name, "child": []},
            },
        )

    def test_update_put_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.put(
                path=reverse(viewname=self.detail_name, kwargs={"pk": self.role.pk}),
                data={
                    "display_name": "new_display_name",
                    "child": [{"id": self.child.pk}],
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_update(
            log=log,
            obj=self.role,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_patch(self):
        new_display_name = "new_display_name"
        prev_display_name = self.role.display_name
        self.client.patch(
            path=reverse(viewname=self.detail_name, kwargs={"pk": self.role.pk}),
            data={
                "display_name": "new_display_name",
                "child": [{"id": self.child.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_update(
            log=log,
            obj=self.role,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            object_changes={
                "current": {"display_name": new_display_name, "child": [self.child.display_name]},
                "previous": {"display_name": prev_display_name, "child": []},
            },
        )

    def test_update_patch_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(viewname=self.detail_name, kwargs={"pk": self.role.pk}),
                data={
                    "display_name": "new_display_name",
                    "child": [{"id": self.child.pk}],
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_update(
            log=log,
            obj=self.role,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_patch_failed(self):
        response: Response = self.client.patch(
            path=reverse(viewname=self.detail_name, kwargs={"pk": self.role.pk}),
            data={
                "display_name": "new_display_name",
                "child": [{"id": -1}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_log_update(
            log=log,
            obj=self.role,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.test_user,
        )
