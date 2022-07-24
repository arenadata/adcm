from datetime import datetime

from audit.models import (
    AUDIT_OPERATION_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from django.urls import reverse

from adcm.tests.base import BaseTestCase


class TestToken(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.audit_operation_create_token = AUDIT_OPERATION_MAP["GetAuthToken"]["POST"]

    def check_log(self, log: AuditLog):
        assert log.audit_object.object_id == self.test_user.pk
        assert log.audit_object.object_name == self.audit_operation_create_token.object_type
        assert log.audit_object.object_type == AuditObjectType.Token.value
        assert not log.audit_object.is_deleted
        assert log.operation_name == self.audit_operation_create_token.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        self.client.post(
            path=reverse("rbac:token"),
            data={
                "username": self.test_user_username,
                "password": self.test_user_password,
            },
        )

        log_1: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(log_1)

        self.client.post(
            path=reverse("token"),
            data={
                "username": self.test_user_username,
                "password": self.test_user_password,
            },
        )

        log_2: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(log_2)
        assert log_1.pk != log_2.pk
