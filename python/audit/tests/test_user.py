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
from pathlib import Path
from secrets import token_hex

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import ObjectType, Prototype
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
    AuditSession,
    AuditUser,
)


class TestUserAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.username = "test_username"
        self.list_name = "v1:rbac:user-list"
        self.detail_name = "v1:rbac:user-detail"
        self.user_created_str = "User created"

    def check_log(
        self,
        log: AuditLog,
        operation_result: AuditLogOperationResult,
        user: User,
        object_changes: dict | None = None,
        operation_name: str = "User updated",
    ) -> None:
        if object_changes is None:
            object_changes = {}

        self.assertEqual(log.audit_object.object_id, self.test_user.id)
        self.assertEqual(log.audit_object.object_name, self.test_user.username)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.USER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, user.username)
        self.assertEqual(log.object_changes, object_changes)

    def _recreate_user(self, username: str) -> tuple[User, str]:
        new_password = token_hex(nbytes=10)
        User.objects.get(username=username).delete()

        return self.get_new_user(username=username, password=new_password), new_password

    def _make_audit_logs(self, username: str, password: str, bundle_pk: int) -> tuple[AuditLog, AuditSession]:
        with self.another_user_logged_in(username=username, password=password):
            self.client.post(
                path=reverse(viewname="v1:rbac:token"),
                data={
                    "username": username,
                    "password": password,
                },
                content_type=APPLICATION_JSON,
            )
            audit_session = AuditSession.objects.order_by("-pk").first()

            self.client.post(
                path=reverse(viewname="v1:cluster"),
                data={
                    "prototype_id": Prototype.objects.get(bundle_id=bundle_pk, type=ObjectType.CLUSTER).pk,
                    "name": "test_cluster_name",
                    "display_name": "test_cluster_display_name",
                    "bundle_id": bundle_pk,
                },
                content_type=APPLICATION_JSON,
            )
            audit_log = AuditLog.objects.order_by("-pk").first()

        return audit_log, audit_session

    def test_create(self):
        response: Response = self.client.post(
            path=reverse(viewname=self.list_name),
            data={
                "username": self.username,
                "password": "test_password",
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(log.audit_object.object_id, response.data["id"])
        self.assertEqual(log.audit_object.object_name, self.username)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.USER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, self.user_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.SUCCESS)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.test_user.username)
        self.assertEqual(log.object_changes, {})

        self.client.post(
            path=reverse(viewname=self.list_name),
            data={
                "username": self.username,
                "password": "test_pass",
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.user_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.FAIL)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.test_user.username)
        self.assertEqual(log.object_changes, {})

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname=self.list_name),
                data={
                    "username": self.username,
                    "password": "test_pass",
                },
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.user_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.DENIED)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.no_rights_user.username)
        self.assertEqual(log.object_changes, {})

    def test_delete(self):
        self.client.delete(
            path=reverse(viewname=self.detail_name, kwargs={"pk": self.no_rights_user.pk}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(log.audit_object.object_id, self.no_rights_user.pk)
        self.assertEqual(log.audit_object.object_name, self.no_rights_user.username)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.USER)
        self.assertEqual(log.audit_object.is_deleted, False)
        self.assertEqual(log.operation_name, "User deleted")
        self.assertEqual(log.operation_type, AuditLogOperationType.DELETE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.SUCCESS)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.test_user.username)
        self.assertEqual(log.object_changes, {})

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(viewname=self.detail_name, kwargs={"pk": self.test_user.pk}),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(log.audit_object.object_id, self.test_user.pk)
        self.assertEqual(log.audit_object.object_name, self.test_user.username)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.USER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, "User deleted")
        self.assertEqual(log.operation_type, AuditLogOperationType.DELETE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.DENIED)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.no_rights_user.username)
        self.assertEqual(log.object_changes, {})

    def test_update_put(self):
        prev_first_name = self.test_user.first_name
        prev_is_superuser = self.test_user.is_superuser
        new_test_first_name = "test_first_name"
        admin = User.objects.get(username="admin")
        self.client.login(username="admin", password="admin")
        self.client.put(
            path=reverse(viewname=self.detail_name, kwargs={"pk": self.test_user.pk}),
            data={
                "username": self.test_user_username,
                "first_name": new_test_first_name,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.test_user.refresh_from_db()
        self.check_log(
            log=log,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=admin,
            object_changes={
                "current": {
                    "first_name": new_test_first_name,
                    "is_superuser": self.test_user.is_superuser,
                },
                "previous": {
                    "first_name": prev_first_name,
                    "is_superuser": prev_is_superuser,
                },
            },
        )

    def test_update_put_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.put(
                path=reverse(viewname=self.detail_name, kwargs={"pk": self.test_user.pk}),
                data={
                    "username": self.test_user_username,
                    "password": self.test_user_password,
                    "first_name": "test_first_name",
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(log=log, operation_result=AuditLogOperationResult.DENIED, user=self.no_rights_user)

    def test_update_patch(self):
        prev_first_name = self.test_user.first_name
        new_test_first_name = "test_first_name"
        self.client.patch(
            path=reverse(viewname=self.detail_name, kwargs={"pk": self.test_user.pk}),
            data={"first_name": new_test_first_name},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.test_user.refresh_from_db()
        self.check_log(
            log=log,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            object_changes={
                "current": {"first_name": new_test_first_name},
                "previous": {"first_name": prev_first_name},
            },
        )

    def test_update_patch_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(viewname=self.detail_name, kwargs={"pk": self.test_user.pk}),
                data={"first_name": "test_first_name"},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(log=log, operation_result=AuditLogOperationResult.DENIED, user=self.no_rights_user)

    def test_reset_failed_login_attempts_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-reset-failed-login-attempts", kwargs={"pk": self.test_user.pk}),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_log(
            log=log,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            operation_name="User login attempts reset",
        )

    def test_reset_failed_login_attempts_fail(self):
        user_pks = User.objects.all().values_list("pk", flat=True).order_by("-pk")
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-reset-failed-login-attempts", kwargs={"pk": user_pks[0] + 1}),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertIsNone(log.audit_object)
        self.assertEqual(log.operation_name, "User login attempts reset")
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.FAIL)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.test_user.username)
        self.assertEqual(log.object_changes, {})

    def test_reset_failed_login_attempts_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:rbac:user-reset-failed-login-attempts", kwargs={"pk": self.test_user.pk}),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
            operation_name="User login attempts reset",
        )

    def test_recreate_user_same_username_different_audit_users_success(self):
        initial_audit_users_count = AuditUser.objects.count()
        with self.another_user_logged_in(username="admin", password="admin"):
            bundle = self.upload_and_load_bundle(
                path=Path(self.base_dir, "python/audit/tests/files/test_cluster_bundle.tar")
            )

        username, password = "test_user_recreate_username", token_hex(10)
        with self.another_user_logged_in(username="admin", password="admin"):
            user = self.get_new_user(username=username, password=password)
        self.assertEqual(AuditUser.objects.count(), initial_audit_users_count + 1)
        old_user_pk = user.pk

        audit_log_1, audit_session_1 = self._make_audit_logs(username=username, password=password, bundle_pk=bundle.pk)
        audit_log_1_pk, audit_session_1_pk = audit_log_1.pk, audit_session_1.pk
        self.assertEqual(audit_log_1.user.username, username)
        self.assertEqual(audit_session_1.user.username, username)

        with self.another_user_logged_in(username="admin", password="admin"):
            new_user, new_password = self._recreate_user(username=username)
        self.assertEqual(AuditUser.objects.count(), initial_audit_users_count + 2)
        self.assertEqual(AuditUser.objects.filter(username=username).count(), 2)
        self.assertNotEqual(old_user_pk, new_user.pk)
        self.assertEqual(AuditLog.objects.get(pk=audit_log_1_pk).user.username, username)
        self.assertEqual(AuditSession.objects.get(pk=audit_session_1_pk).user.username, username)

        audit_log_2, audit_session_2 = self._make_audit_logs(
            username=new_user.username, password=new_password, bundle_pk=bundle.pk
        )
        self.assertEqual(audit_log_2.user.username, new_user.username)
        self.assertEqual(audit_session_2.user.username, new_user.username)
