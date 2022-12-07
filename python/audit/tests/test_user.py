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

from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from rbac.models import User


class TestUser(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.username = "test_username"
        self.list_name = "rbac:user-list"
        self.detail_name = "rbac:user-detail"
        self.user_created_str = "User created"

    def check_log(
        self,
        log: AuditLog,
        operation_result: AuditLogOperationResult,
        user: User,
        object_changes: dict | None = None,
    ) -> None:
        if object_changes is None:
            object_changes = {}

        self.assertEqual(log.audit_object.object_id, self.test_user.id)
        self.assertEqual(log.audit_object.object_name, self.test_user.username)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.User)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, "User updated")
        self.assertEqual(log.operation_type, AuditLogOperationType.Update)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, object_changes)

    def test_create(self):
        response: Response = self.client.post(
            path=reverse(self.list_name),
            data={
                "username": self.username,
                "password": "test_password",
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(log.audit_object.object_id, response.data["id"])
        self.assertEqual(log.audit_object.object_name, self.username)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.User)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, self.user_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.Create)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Success)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.test_user.pk)
        self.assertEqual(log.object_changes, {})

        self.client.post(
            path=reverse(self.list_name),
            data={
                "username": self.username,
                "password": "test_password",
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.user_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.Create)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Fail)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.test_user.pk)
        self.assertEqual(log.object_changes, {})

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(self.list_name),
                data={
                    "username": self.username,
                    "password": "test_password",
                },
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.user_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.Create)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Denied)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.no_rights_user.pk)
        self.assertEqual(log.object_changes, {})

    def test_delete(self):
        self.client.delete(
            path=reverse(self.detail_name, kwargs={"pk": self.no_rights_user.pk}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(log.audit_object.object_id, self.no_rights_user.pk)
        self.assertEqual(log.audit_object.object_name, self.no_rights_user.username)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.User)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, "User deleted")
        self.assertEqual(log.operation_type, AuditLogOperationType.Delete)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Success)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.test_user.pk)
        self.assertEqual(log.object_changes, {})

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(self.detail_name, kwargs={"pk": self.test_user.pk}),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(log.audit_object.object_id, self.test_user.pk)
        self.assertEqual(log.audit_object.object_name, self.test_user.username)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.User)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, "User deleted")
        self.assertEqual(log.operation_type, AuditLogOperationType.Delete)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Denied)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.no_rights_user.pk)
        self.assertEqual(log.object_changes, {})

    def test_update_put(self):
        prev_first_name = self.test_user.first_name
        prev_is_superuser = self.test_user.is_superuser
        new_test_first_name = "test_first_name"
        self.client.put(
            path=reverse(self.detail_name, kwargs={"pk": self.test_user.pk}),
            data={
                "username": self.test_user_username,
                "password": self.test_user_password,
                "first_name": new_test_first_name,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.test_user.refresh_from_db()
        self.check_log(
            log=log,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
            object_changes={
                "current": {
                    "password": "******",
                    "first_name": new_test_first_name,
                    "is_superuser": self.test_user.is_superuser,
                },
                "previous": {
                    "password": "******",
                    "first_name": prev_first_name,
                    "is_superuser": prev_is_superuser,
                },
            },
        )

    def test_update_put_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.put(
                path=reverse(self.detail_name, kwargs={"pk": self.test_user.pk}),
                data={
                    "username": self.test_user_username,
                    "password": self.test_user_password,
                    "first_name": "test_first_name",
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user)

    def test_update_patch(self):
        prev_first_name = self.test_user.first_name
        new_test_first_name = "test_first_name"
        self.client.patch(
            path=reverse(self.detail_name, kwargs={"pk": self.test_user.pk}),
            data={"first_name": new_test_first_name},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.test_user.refresh_from_db()
        self.check_log(
            log=log,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
            object_changes={
                "current": {"first_name": new_test_first_name},
                "previous": {"first_name": prev_first_name},
            },
        )

    def test_update_patch_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(self.detail_name, kwargs={"pk": self.test_user.pk}),
                data={"first_name": "test_first_name"},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user)
