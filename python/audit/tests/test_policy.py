from datetime import datetime

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import Bundle, Cluster, Prototype
from django.urls import reverse
from rbac.models import Policy, Role, RoleTypes
from rest_framework.response import Response

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestPolicy(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.name = "test_policy"
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster_name = "test_cluster"
        self.cluster = Cluster.objects.create(name=self.cluster_name, prototype=prototype)
        self.role = Role.objects.create(
            name="test_role",
            display_name="test_role",
            type=RoleTypes.role,
            parametrized_by_type=["cluster"],
            module_name="rbac.roles",
            class_name="ObjectRole",
        )
        self.policy = Policy.objects.create(name="test_policy_2", built_in=False)

    def check_policy_updated(self, log: AuditLog) -> None:
        assert log.audit_object.object_id == self.policy.pk
        assert log.audit_object.object_name == self.policy.name
        assert log.audit_object.object_type == AuditObjectType.Policy
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Policy updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("rbac:policy-list"),
            data={
                "name": self.name,
                "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
            },
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.name
        assert log.audit_object.object_type == AuditObjectType.Policy
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Policy created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_put(self):
        self.client.put(
            path=reverse("rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data={
                "name": self.policy.name,
                "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
                "description": "new_test_description",
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_policy_updated(log)

    def test_update_patch(self):
        self.client.patch(
            path=reverse("rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data={
                "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
                "description": "new_test_description",
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_policy_updated(log)
