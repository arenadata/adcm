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

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestRole(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.role_display_name = "test_role"
        self.child = Role.objects.create(
            name="test_child_role",
            display_name="test_child_role",
            type=RoleTypes.business,
        )
        self.role = Role.objects.create(name="test_role_2", built_in=False)

    def check_role_updated(self, log: AuditLog) -> None:
        assert log.audit_object.object_id == self.role.pk
        assert log.audit_object.object_name == self.role.name
        assert log.audit_object.object_type == AuditObjectType.Role
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Role updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("rbac:role-list"),
            data={
                "display_name": self.role_display_name,
                "child": [{"id": self.child.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.role_display_name
        assert log.audit_object.object_type == AuditObjectType.Role
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Role created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        self.client.post(
            path=reverse("rbac:role-list"),
            data={
                "display_name": self.role_display_name,
                "child": [{"id": self.child.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == "Role created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Fail
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_put(self):
        self.client.put(
            path=reverse("rbac:role-detail", kwargs={"pk": self.role.pk}),
            data={
                "display_name": "new_display_name",
                "child": [{"id": self.child.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_role_updated(log)

    def test_update_patch(self):
        self.client.patch(
            path=reverse("rbac:role-detail", kwargs={"pk": self.role.pk}),
            data={
                "display_name": "new_display_name",
                "child": [{"id": self.child.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_role_updated(log)
