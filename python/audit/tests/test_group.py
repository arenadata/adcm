from datetime import datetime

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from django.urls import reverse
from rbac.models import Group
from rest_framework.response import Response

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestGroup(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.name = "test_group"
        self.group = Group.objects.create(name="test_group_2")

    def check_group_updated(self, log: AuditLog) -> None:
        assert log.audit_object.object_id == self.group.pk
        assert log.audit_object.object_name == self.group.name
        assert log.audit_object.object_type == AuditObjectType.Group
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Group updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("rbac:group-list"),
            data={"name": self.name},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.name
        assert log.audit_object.object_type == AuditObjectType.Group
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Group created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        self.client.post(
            path=reverse("rbac:group-list"),
            data={"name": self.name},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == "Group created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Fail
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_put(self):
        self.client.put(
            path=reverse("rbac:group-detail", kwargs={"pk": self.group.pk}),
            data={
                "name": self.group.name,
                "display_name": "new_display_name",
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_group_updated(log)

    def test_update_patch(self):
        self.client.patch(
            path=reverse("rbac:group-detail", kwargs={"pk": self.group.pk}),
            data={"display_name": "new_display_name"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_group_updated(log)
