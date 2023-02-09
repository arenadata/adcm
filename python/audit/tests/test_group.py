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
from rbac.models import Group, User
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestGroupAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.name = "test_group"
        self.description = "test_description"
        self.group = Group.objects.create(name="test_group_2", description=self.description)
        self.list_name = "rbac:group-list"
        self.detail_name = "rbac:group-detail"
        self.group_created_str = "Group created"
        self.group_updated_str = "Group updated"

    def check_log(
        self,
        log: AuditLog,
        operation_name: str,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
        object_changes: dict | None = None,
    ) -> None:
        if object_changes is None:
            object_changes = {}

        self.assertEqual(log.audit_object.object_id, self.group.pk)
        self.assertEqual(log.audit_object.object_name, self.group.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.GROUP)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, object_changes)

    def test_create(self):
        response: Response = self.client.post(
            path=reverse(self.list_name),
            data={"name": self.name},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        group = Group.objects.get(pk=response.data["id"])
        self.assertEqual(log.audit_object.object_id, response.data["id"])
        self.assertEqual(log.audit_object.object_name, group.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.GROUP)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, self.group_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.SUCCESS)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.test_user.pk)
        self.assertIsInstance(log.object_changes, dict)

        self.client.post(
            path=reverse(self.list_name),
            data={"name": self.name},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.group_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.FAIL)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.test_user.pk)
        self.assertIsInstance(log.object_changes, dict)

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(self.list_name),
                data={"name": self.name},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.group_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.DENIED)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.no_rights_user.pk)
        self.assertIsInstance(log.object_changes, dict)

    def test_delete(self):
        self.client.delete(
            path=reverse(self.detail_name, kwargs={"pk": self.group.pk}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Group deleted",
            operation_type=AuditLogOperationType.DELETE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(self.detail_name, kwargs={"pk": self.group.pk}),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            operation_name="Group deleted",
            operation_type=AuditLogOperationType.DELETE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_put(self):
        new_description = "new_test_description"
        prev_description = self.group.description
        self.client.put(
            path=reverse(self.detail_name, kwargs={"pk": self.group.pk}),
            data={
                "name": self.group.name,
                "description": new_description,
                "user": [{"id": self.test_user.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.check_log(
            log=log,
            operation_name=self.group_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            object_changes={
                "current": {"description": new_description, "user": [self.test_user.username]},
                "previous": {"description": prev_description, "user": []},
            },
        )

    def test_update_put_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.put(
                path=reverse(self.detail_name, kwargs={"pk": self.group.pk}),
                data={
                    "name": self.group.name,
                    "display_name": "new_display_name",
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            operation_name=self.group_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_patch(self):
        new_description = "new_test_description"
        self.client.patch(
            path=reverse(self.detail_name, kwargs={"pk": self.group.pk}),
            data={
                "description": new_description,
                "user": [{"id": self.test_user.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name=self.group_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            object_changes={
                "current": {"description": new_description, "user": [self.test_user.username]},
                "previous": {"description": self.description, "user": []},
            },
        )

    def test_update_patch_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(self.detail_name, kwargs={"pk": self.group.pk}),
                data={"display_name": "new_display_name"},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            operation_name=self.group_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )
