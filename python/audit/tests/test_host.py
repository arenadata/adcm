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
from typing import Optional

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import (
    Bundle,
    Cluster,
    ConfigLog,
    Host,
    HostProvider,
    ObjectConfig,
    Prototype,
)
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestHost(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        provider_prototype = Prototype.objects.create(bundle=self.bundle, type="provider")
        self.host_prototype = Prototype.objects.create(bundle=self.bundle, type="host")
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
        self.host_created_str = "Host created"

    def check_host_created(self, log: AuditLog, res: Response) -> None:
        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.fqdn
        assert log.audit_object.object_type == AuditObjectType.Host
        assert not log.audit_object.is_deleted
        assert log.operation_name == self.host_created_str
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def check_host_updated(
        self,
        log: AuditLog,
        operation_result: AuditLogOperationResult = AuditLogOperationResult.Success,
        user: Optional[User] = None,
    ) -> None:
        if user is None:
            user = self.test_user

        assert log.audit_object.object_id == self.host.pk
        assert log.audit_object.object_name == self.host.fqdn
        assert log.audit_object.object_type == AuditObjectType.Host
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Host configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

    def check_host_deleted(
        self,
        log: AuditLog,
        operation_result: AuditLogOperationResult = AuditLogOperationResult.Success,
        user: Optional[User] = None,
    ) -> None:
        if user is None:
            user = self.test_user

        assert log.audit_object.object_id == self.host.pk
        assert log.audit_object.object_name == self.host.fqdn
        assert log.audit_object.object_type == AuditObjectType.Host
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Host deleted"
        assert log.operation_type == AuditLogOperationType.Delete
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

    def check_denied(self, log: AuditLog) -> None:
        assert not log.audit_object
        assert log.operation_name == self.host_created_str
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Denied
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.no_rights_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(path=reverse("host"), data={})

        assert res.status_code == HTTP_400_BAD_REQUEST

        res: Response = self.client.post(
            path=reverse("host"),
            data={
                "prototype_id": self.host_prototype.pk,
                "provider_id": self.provider.pk,
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
        assert log.operation_name == self.host_created_str
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Fail
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse("host"),
                data={
                    "prototype_id": self.host_prototype.pk,
                    "provider_id": self.provider.pk,
                    "fqdn": self.fqdn,
                },
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_denied(log=log)

    def test_delete(self):
        self.client.delete(path=reverse("host-details", kwargs={"host_id": self.host.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_deleted(log=log)

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=reverse("host-details", kwargs={"host_id": self.host.pk})
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_404_NOT_FOUND
        self.check_host_deleted(
            log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user
        )

    def test_delete_failed(self):
        self.host.cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type="cluster"),
            name="test_cluster",
        )
        self.host.save(update_fields=["cluster"])

        self.client.delete(path=reverse("host-details", kwargs={"host_id": self.host.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_deleted(log=log, operation_result=AuditLogOperationResult.Fail)

    def test_delete_via_provider(self):
        self.client.delete(
            path=reverse(
                "host-details", kwargs={"host_id": self.host.pk, "provider_id": self.provider.pk}
            ),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_deleted(log)

    def test_delete_via_provider_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=reverse(
                    "host-details",
                    kwargs={"host_id": self.host.pk, "provider_id": self.provider.pk},
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_404_NOT_FOUND
        self.check_host_deleted(
            log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user
        )

    def test_delete_via_provider_failed(self):
        self.host.cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type="cluster"),
            name="test_cluster",
        )
        self.host.save(update_fields=["cluster"])

        self.client.delete(
            path=reverse(
                "host-details", kwargs={"host_id": self.host.pk, "provider_id": self.provider.pk}
            ),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_deleted(log=log, operation_result=AuditLogOperationResult.Fail)

    def test_create_via_provider(self):
        res: Response = self.client.post(
            path=reverse("host", kwargs={"provider_id": self.provider.pk}),
            data={"fqdn": self.fqdn},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_created(log, res)

    def test_create_via_provider_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse("host", kwargs={"provider_id": self.provider.pk}),
                data={"fqdn": self.fqdn},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_404_NOT_FOUND
        self.check_denied(log=log)

    def test_update_and_restore(self):
        self.client.post(
            path=reverse("config-history", kwargs={"host_id": self.host.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated(log=log)

        res: Response = self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={"host_id": self.host.pk, "version": 1},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.check_host_updated(log=log)

    def test_update_and_restore_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse("config-history", kwargs={"host_id": self.host.pk}),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_host_updated(
            log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user
        )

        with self.no_rights_user_logged_in:
            res: Response = self.client.patch(
                path=reverse(
                    "config-history-version-restore",
                    kwargs={"host_id": self.host.pk, "version": 1},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_host_updated(
            log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user
        )

    def test_update_and_restore_via_provider(self):
        self.client.post(
            path=reverse(
                "config-history",
                kwargs={"provider_id": self.provider.pk, "host_id": self.host.pk},
            ),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated(log=log)

        res: Response = self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={"provider_id": self.provider.pk, "host_id": self.host.pk, "version": 1},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.check_host_updated(log=log)

    def test_update_and_restore_via_provider_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse(
                    "config-history",
                    kwargs={"provider_id": self.provider.pk, "host_id": self.host.pk},
                ),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_host_updated(
            log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user
        )

        with self.no_rights_user_logged_in:
            res: Response = self.client.patch(
                path=reverse(
                    "config-history-version-restore",
                    kwargs={"provider_id": self.provider.pk, "host_id": self.host.pk, "version": 1},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_host_updated(
            log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user
        )
