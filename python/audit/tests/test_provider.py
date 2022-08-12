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
from cm.models import Bundle, ConfigLog, HostProvider, ObjectConfig, Prototype
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from adcm.tests.base import BaseTestCase


class TestProvider(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.prototype = Prototype.objects.create(bundle=self.bundle, type="provider")
        self.name = "test_provider"

    @staticmethod
    def check_provider_updated(
        log: AuditLog,
        provider: HostProvider,
        operation_result: AuditLogOperationResult,
        user: User,
    ) -> None:
        assert log.audit_object.object_id == provider.pk
        assert log.audit_object.object_name == provider.name
        assert log.audit_object.object_type == AuditObjectType.Provider
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Provider configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("provider"),
            data={
                "name": self.name,
                "prototype_id": self.prototype.pk,
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

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse("provider"),
                data={
                    "name": self.name,
                    "prototype_id": self.prototype.pk,
                },
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        assert not log.audit_object
        assert log.operation_name == "Provider created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Denied
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.no_rights_user.pk
        assert isinstance(log.object_changes, dict)

    def test_delete(self):
        provider = HostProvider.objects.create(
            name="test_provider",
            prototype=self.prototype,
        )

        self.client.delete(path=reverse("provider-details", kwargs={"provider_id": provider.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == provider.pk
        assert log.audit_object.object_name == provider.name
        assert log.audit_object.object_type == AuditObjectType.Provider
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Provider deleted"
        assert log.operation_type == AuditLogOperationType.Delete
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_delete_denied(self):
        provider = HostProvider.objects.create(
            name="test_provider",
            prototype=self.prototype,
        )

        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=reverse("provider-details", kwargs={"provider_id": provider.pk})
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_404_NOT_FOUND
        assert log.audit_object.object_id == provider.pk
        assert log.audit_object.object_name == provider.name
        assert log.audit_object.object_type == AuditObjectType.Provider
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Provider deleted"
        assert log.operation_type == AuditLogOperationType.Delete
        assert log.operation_result == AuditLogOperationResult.Denied
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.no_rights_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_and_restore(self):
        config = ObjectConfig.objects.create(current=1, previous=1)
        provider = HostProvider.objects.create(
            prototype=self.prototype, name="test_provider", config=config
        )

        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.client.post(
            path=reverse("config-history", kwargs={"provider_id": provider.pk}),
            data={"config": {}},
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_provider_updated(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

        res: Response = self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={"provider_id": provider.pk, "version": 1},
            ),
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.check_provider_updated(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_update_and_restore_denied(self):
        config = ObjectConfig.objects.create(current=1, previous=1)
        provider = HostProvider.objects.create(
            prototype=self.prototype, name="test_provider", config=config
        )

        ConfigLog.objects.create(obj_ref=config, config="{}")
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse("config-history", kwargs={"provider_id": provider.pk}),
                data={"config": {}},
                content_type="application/json",
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_provider_updated(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

        with self.no_rights_user_logged_in:
            res: Response = self.client.patch(
                path=reverse(
                    "config-history-version-restore",
                    kwargs={"provider_id": provider.pk, "version": 1},
                ),
                content_type="application/json",
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_provider_updated(
            log=log,
            provider=provider,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )
