from datetime import datetime

from audit.models import (
    AUDIT_OPERATION_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestUser(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.username = "test_username"
        self.audit_operation_create_user = AUDIT_OPERATION_MAP["UserViewSet"]["POST"]

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
        assert log.audit_object.object_type == AuditObjectType.User.value
        assert not log.audit_object.is_deleted
        assert log.operation_name == self.audit_operation_create_user.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
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
        assert log.operation_name == self.audit_operation_create_user.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Failed.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
