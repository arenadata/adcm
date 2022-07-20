from datetime import datetime

from rest_framework.response import Response

from adcm.tests.base import BaseTestCase
from audit.models import (
    AUDIT_OPERATION_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
)


class TestCluster(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.upload_bundle()
        res: Response = self.load_bundle()
        self.bundle_id = res.data["id"]
        self.test_cluster_name = "test_cluster"
        self.audit_operation_create_cluster = AUDIT_OPERATION_MAP["ClusterList"]["POST"]

    def test_cluster_create(self):
        res: Response = self.create_cluster(self.bundle_id, self.test_cluster_name)

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.test_cluster_name
        assert log.audit_object.object_type == "cluster"
        assert not log.audit_object.is_deleted
        assert log.operation_name == self.audit_operation_create_cluster.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        self.create_cluster(self.bundle_id, self.test_cluster_name)

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == self.audit_operation_create_cluster.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Failed.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
