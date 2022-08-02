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
from rest_framework.response import Response

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestUser(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.username = "test_username"

    def check_user_updated(self, log: AuditLog) -> None:
        assert log.audit_object.object_id == self.test_user.id
        assert log.audit_object.object_name == self.test_user.username
        assert log.audit_object.object_type == AuditObjectType.User
        assert not log.audit_object.is_deleted
        assert log.operation_name == "User updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("rbac:user-list"),
            data={
                "username": self.username,
                "password": "test_password",
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.username
        assert log.audit_object.object_type == AuditObjectType.User
        assert not log.audit_object.is_deleted
        assert log.operation_name == "User created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        self.client.post(
            path=reverse("rbac:user-list"),
            data={
                "username": self.username,
                "password": "test_password",
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == "User created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Fail
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_put(self):
        self.client.put(
            path=reverse("rbac:user-detail", kwargs={"pk": self.test_user.pk}),
            data={
                "username": self.test_user_username,
                "password": self.test_user_password,
                "first_name": "test_first_name",
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_user_updated(log)

    def test_update_patch(self):
        self.client.patch(
            path=reverse("rbac:user-detail", kwargs={"pk": self.test_user.pk}),
            data={"first_name": "test_first_name"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_user_updated(log)
