from datetime import datetime

from audit.models import (
    AUDIT_OPERATION_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
)
from cm.models import Bundle
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestBundle(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.audit_operation_upload_bundle = AUDIT_OPERATION_MAP["UploadBundle"]["POST"]
        self.audit_operation_load_bundle = AUDIT_OPERATION_MAP["LoadBundle"]["POST"]

    def upload_bundle_and_check(self):
        self.upload_bundle()

        res: Response = self.load_bundle()
        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == "hc_acl_in_service_noname"
        assert log.audit_object.object_type == "bundle"
        assert not log.audit_object.is_deleted
        assert log.operation_name == self.audit_operation_load_bundle.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        return res

    def test_upload_success(self):
        self.upload_bundle()

        log: AuditLog = AuditLog.objects.first()

        assert not log.audit_object
        assert log.operation_name == self.audit_operation_upload_bundle.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_upload_fail(self):
        with open(self.test_bundle_path, encoding="utf-8") as f:
            self.client.post(
                path=reverse("upload-bundle"),
                data={"no_file": f},
            )

        log: AuditLog = AuditLog.objects.first()

        assert not log.audit_object
        assert log.operation_name == self.audit_operation_upload_bundle.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Failed.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_load(self):
        self.upload_bundle_and_check()
        self.load_bundle()

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == self.audit_operation_load_bundle.name
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Failed.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_load_and_delete(self):
        res: Response = self.upload_bundle_and_check()

        Bundle.objects.get(pk=res.data["id"]).delete()
        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.is_deleted
