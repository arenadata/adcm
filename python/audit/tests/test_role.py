from datetime import datetime

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from django.urls import reverse
from rbac.models import Role, RoleTypes
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestRole(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.role_display_name = "test_role"
        self.child = Role.objects.create(
            name="test_child_role",
            display_name="test_child_role",
            type=RoleTypes.business,
        )

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("rbac:role-list"),
            data={
                "display_name": self.role_display_name,
                "child[0]id": self.child.pk,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.role_display_name
        assert log.audit_object.object_type == AuditObjectType.Role.value
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Role created"
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        self.client.post(
            path=reverse("rbac:role-list"),
            data={
                "display_name": self.role_display_name,
                'child[0]id': self.child.pk,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == "Role created"
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Fail.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
