from datetime import datetime

from audit.models import AuditLog, AuditLogOperationResult, AuditLogOperationType
from cm.models import Bundle, Cluster, ConfigLog, ObjectConfig, Prototype
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestConfigLog(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.config = ObjectConfig.objects.create(current=1, previous=1)
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        Cluster.objects.create(prototype=prototype, config=self.config)
        ConfigLog.objects.create(obj_ref=self.config, config="{}")

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("config-log-list"),
            data={"obj_ref": self.config.pk, "config": "{}"},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == str(ConfigLog.objects.get(pk=res.data["id"]))
        assert log.audit_object.object_type == "???"
        assert not log.audit_object.is_deleted
        assert log.operation_name == "???"
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
