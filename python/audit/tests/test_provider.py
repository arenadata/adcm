from datetime import datetime

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import Bundle, ConfigLog, HostProvider, ObjectConfig, Prototype
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.tests.base import BaseTestCase


class TestProvider(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        self.prototype = Prototype.objects.create(bundle=bundle, type="provider")
        self.name = "test_provider"

    def check_provider_updated(self, log: AuditLog, provider: HostProvider) -> None:
        assert log.audit_object.object_id == provider.pk
        assert log.audit_object.object_name == provider.name
        assert log.audit_object.object_type == AuditObjectType.Provider
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Provider configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("provider"),
            data={
                "name": self.name,
                "prototype_id": self.prototype.id,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.name
        assert log.audit_object.object_type == AuditObjectType.Provider
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Provider created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        self.client.post(
            path=reverse("provider"),
            data={
                "name": self.name,
                "prototype_id": self.prototype.id,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == "Provider created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Fail
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_and_restore(self):
        config = ObjectConfig.objects.create(current=1, previous=1)
        provider = HostProvider.objects.create(
            prototype=self.prototype, name="test_provider", config=config
        )

        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.client.post(
            path=f"/api/v1/provider/{provider.pk}/config/history/",
            data={"config": {}},
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_provider_updated(log, provider)

        res: Response = self.client.patch(
            path=f"/api/v1/provider/{provider.pk}/config/history/1/restore/",
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.check_provider_updated(log, provider)
