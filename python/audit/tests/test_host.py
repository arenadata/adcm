# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import Bundle, ConfigLog, Host, HostProvider, ObjectConfig, Prototype
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.tests.base import BaseTestCase


class TestHost(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        provider_prototype = Prototype.objects.create(bundle=bundle, type="provider")
        self.host_prototype = Prototype.objects.create(bundle=bundle, type="host")
        self.provider = HostProvider.objects.create(
            name="test_provider",
            prototype=provider_prototype,
        )
        self.fqdn = "test_fqdn"
        config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.host = Host.objects.create(
            fqdn="test_fqdn_2",
            prototype=self.host_prototype,
            provider=self.provider,
            config=config,
        )

    def check_host_created(self, log: AuditLog, res: Response) -> None:
        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.fqdn
        assert log.audit_object.object_type == AuditObjectType.Host
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Host created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def check_host_updated(self, log: AuditLog) -> None:
        assert log.audit_object.object_id == self.host.pk
        assert log.audit_object.object_name == self.host.fqdn
        assert log.audit_object.object_type == AuditObjectType.Host
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Host configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("host"),
            data={
                "prototype_id": self.host_prototype.id,
                "provider_id": self.provider.id,
                "fqdn": self.fqdn,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_created(log, res)

        self.client.post(
            path=reverse("host"),
            data={
                "prototype_id": self.host_prototype.id,
                "provider_id": self.provider.id,
                "fqdn": self.fqdn,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == "Host created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Fail
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create_via_provider(self):
        res: Response = self.client.post(
            path=f"/api/v1/provider/{self.provider.pk}/host/",
            data={"fqdn": self.fqdn},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_created(log, res)

    def test_update_and_restore(self):
        self.client.post(
            path=f"/api/v1/host/{self.host.pk}/config/history/",
            data={"config": {}},
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated(log)

        res: Response = self.client.patch(
            path=f"/api/v1/host/{self.host.pk}/config/history/1/restore/",
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.check_host_updated(log)

    def test_update_and_restore_via_provider(self):
        self.client.post(
            path=f"/api/v1/provider/{self.provider.pk}/host/{self.host.pk}/config/history/",
            data={"config": {}},
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated(log)

        res: Response = self.client.patch(
            path=f"/api/v1/provider/{self.provider.pk}/host/"
            f"{self.host.pk}/config/history/1/restore/",
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.check_host_updated(log)
