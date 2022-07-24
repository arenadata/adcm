import json
from datetime import datetime

from audit.models import (
    AUDIT_OPERATION_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import Bundle, Cluster, Prototype
from django.urls import reverse
from rbac.models import Role, RoleTypes
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestPolicy(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.name = "test_policy"
        self.audit_operation_create_policy = AUDIT_OPERATION_MAP["PolicyViewSet"]["POST"]
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster = Cluster.objects.create(name="test_cluster", prototype=prototype)
        self.role = Role.objects.create(
            name="test_role",
            display_name="test_role",
            type=RoleTypes.role,
            parametrized_by_type=["cluster"],
            module_name="rbac.roles",
            class_name="ObjectRole",
        )

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("rbac:policy-list"),
            data={
                "name": self.name,
                "object": json.dumps([{"id": self.cluster.id, "type": "cluster"}]),
                "role.id": self.role.pk,
                "user[0]id": self.test_user.pk,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.name
        assert log.audit_object.object_type == AuditObjectType.Policy.value
        assert not log.audit_object.is_deleted
        assert log.operation_name == self.audit_operation_create_policy.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        self.client.post(
            path=reverse("rbac:policy-list"),
            data={
                "name": self.name,
                "object": json.dumps([{"id": self.cluster.id, "type": "cluster"}]),
                "role.id": self.role.pk,
                "user[0]id": self.test_user.pk,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == self.audit_operation_create_policy.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Failed.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
