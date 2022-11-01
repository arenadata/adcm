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
from unittest.mock import patch

from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import (
    Action,
    Bundle,
    Cluster,
    ConfigLog,
    Host,
    HostProvider,
    MaintenanceMode,
    ObjectConfig,
    Prototype,
)
from rbac.models import User


class TestHost(BaseTestCase):
    # pylint: disable=too-many-public-methods,too-many-instance-attributes

    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        provider_prototype = Prototype.objects.create(bundle=self.bundle, type="provider")
        self.host_prototype = Prototype.objects.create(bundle=self.bundle, type="host")
        self.provider = HostProvider.objects.create(
            name="test_provider",
            prototype=provider_prototype,
        )
        self.fqdn = "test-fqdn"
        config = ObjectConfig.objects.create(current=0, previous=0)
        self.config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = self.config_log.pk
        config.save(update_fields=["current"])

        self.host = Host.objects.create(
            fqdn="test-fqdn-2",
            prototype=self.host_prototype,
            provider=self.provider,
            config=config,
        )
        self.host_created_str = "Host created"
        self.action_display_name = "test_host_action"
        self.cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type="cluster"),
            name="test_cluster",
        )

    def check_host_created_log(self, log: AuditLog, response: Response) -> None:
        self.assertEqual(log.audit_object.object_id, response.data["id"])
        self.assertEqual(log.audit_object.object_name, self.fqdn)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.Host)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, self.host_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.Create)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Success)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.test_user.pk)
        self.assertEqual(log.object_changes, {})

    def check_host_updated_log(
        self,
        log: AuditLog,
        operation_result: AuditLogOperationResult = AuditLogOperationResult.Success,
        operation_name: str = "Host configuration updated",
        audit_object_name: str = None,
        user: Optional[User] = None,
        object_changes: dict | None = None,
    ) -> None:
        if object_changes is None:
            object_changes = {}
        if user is None:
            user = self.test_user

        self.assertEqual(log.audit_object.object_id, self.host.pk)
        self.assertEqual(log.audit_object.object_name, audit_object_name or self.host.fqdn)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.Host)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.Update)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, object_changes)

    def check_host_deleted_log(
        self,
        log: AuditLog,
        operation_result: AuditLogOperationResult = AuditLogOperationResult.Success,
        user: Optional[User] = None,
    ) -> None:
        if user is None:
            user = self.test_user

        self.assertEqual(log.audit_object.object_id, self.host.pk)
        self.assertEqual(log.audit_object.object_name, self.host.fqdn)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.Host)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, "Host deleted")
        self.assertEqual(log.operation_type, AuditLogOperationType.Delete)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, {})

    def check_cluster_updated_log(
        self,
        log: AuditLog,
        obj: Cluster | None,
        operation_result: AuditLogOperationResult,
        user: User,
        operation_name: str | None = None,
    ):
        if operation_name is None:
            operation_name = f"{self.host.fqdn} host removed"

        if obj:
            self.assertEqual(log.audit_object.object_id, obj.pk)
            self.assertEqual(log.audit_object.object_name, obj.name)
            self.assertEqual(log.audit_object.object_type, AuditObjectType.Cluster)
            self.assertFalse(log.audit_object.is_deleted)
        else:
            self.assertFalse(log.audit_object)

        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.Update)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, {})

    def check_denied(self, log: AuditLog) -> None:
        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.host_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.Create)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Denied)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.no_rights_user.pk)
        self.assertEqual(log.object_changes, {})

    def check_action_log(self, log: AuditLog) -> None:
        self.assertEqual(log.audit_object.object_id, self.host.pk)
        self.assertEqual(log.audit_object.object_name, self.host.fqdn)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.Host)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, f"{self.action_display_name} action launched")
        self.assertEqual(log.operation_type, AuditLogOperationType.Update)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Success)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.object_changes, {})

    def test_create(self):
        response: Response = self.client.post(path=reverse("host"), data={})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        response: Response = self.client.post(
            path=reverse("host"),
            data={
                "prototype_id": self.host_prototype.pk,
                "provider_id": self.provider.pk,
                "fqdn": self.fqdn,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_created_log(log=log, response=response)

        self.client.post(
            path=reverse("host"),
            data={
                "prototype_id": self.host_prototype.id,
                "provider_id": self.provider.id,
                "fqdn": self.fqdn,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.host_created_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.Create)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Fail)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.test_user.pk)
        self.assertEqual(log.object_changes, {})

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse("host"),
                data={
                    "prototype_id": self.host_prototype.pk,
                    "provider_id": self.provider.pk,
                    "fqdn": self.fqdn,
                },
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_denied(log=log)

    def test_delete(self):
        self.client.delete(path=reverse("host-details", kwargs={"host_id": self.host.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_deleted_log(log=log)

    def test_delete_via_cluster(self):
        self.host.cluster = self.cluster
        self.host.save(update_fields=["cluster"])

        self.client.delete(
            path=reverse(
                "host-details",
                kwargs={"cluster_id": self.cluster.pk, "host_id": self.host.pk},
            ),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_cluster_updated_log(
            log=log,
            obj=self.cluster,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_delete_via_cluster_denied(self):
        self.host.cluster = self.cluster
        self.host.save(update_fields=["cluster"])

        with self.no_rights_user_logged_in:
            self.client.delete(
                path=reverse(
                    "host-details",
                    kwargs={"cluster_id": self.cluster.pk, "host_id": self.host.pk},
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_cluster_updated_log(
            log=log,
            obj=self.cluster,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_delete_via_cluster_failed(self):
        self.host.cluster = self.cluster
        self.host.save(update_fields=["cluster"])

        cluster_pks = Cluster.objects.all().values_list("pk", flat=True).order_by("-pk")
        self.client.delete(
            path=reverse(
                "host-details",
                kwargs={"cluster_id": cluster_pks[0] + 1, "host_id": self.host.pk},
            ),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_cluster_updated_log(
            log=log, obj=None, operation_result=AuditLogOperationResult.Fail, user=self.test_user
        )

        host_pks = Host.objects.all().values_list("pk", flat=True).order_by("-pk")
        self.client.delete(
            path=reverse(
                "host-details",
                kwargs={"cluster_id": self.cluster.pk, "host_id": host_pks[0] + 1},
            ),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_cluster_updated_log(
            log=log,
            obj=self.cluster,
            operation_result=AuditLogOperationResult.Fail,
            user=self.test_user,
            operation_name="host removed",
        )

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(path=reverse("host-details", kwargs={"host_id": self.host.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_host_deleted_log(log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user)

    def test_delete_failed(self):
        self.host.cluster = self.cluster
        self.host.save(update_fields=["cluster"])

        self.client.delete(path=reverse("host-details", kwargs={"host_id": self.host.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_deleted_log(log=log, operation_result=AuditLogOperationResult.Fail)

    def test_delete_via_provider(self):
        self.client.delete(
            path=reverse("host-details", kwargs={"host_id": self.host.pk, "provider_id": self.provider.pk}),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_deleted_log(log)

    def test_delete_via_provider_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(
                    "host-details",
                    kwargs={"host_id": self.host.pk, "provider_id": self.provider.pk},
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_host_deleted_log(log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user)

    def test_delete_via_provider_failed(self):
        self.host.cluster = self.cluster
        self.host.save(update_fields=["cluster"])

        self.client.delete(
            path=reverse("host-details", kwargs={"host_id": self.host.pk, "provider_id": self.provider.pk}),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_deleted_log(log=log, operation_result=AuditLogOperationResult.Fail)

    def test_create_via_provider(self):
        response: Response = self.client.post(
            path=reverse("host", kwargs={"provider_id": self.provider.pk}),
            data={"fqdn": self.fqdn},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_created_log(log, response)

    def test_create_via_provider_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse("host", kwargs={"provider_id": self.provider.pk}),
                data={"fqdn": self.fqdn},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_denied(log=log)

    def test_update_config_and_restore(self):
        self.client.post(
            path=reverse("config-history", kwargs={"host_id": self.host.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated_log(log=log)

        response: Response = self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={"host_id": self.host.pk, "version": self.config_log.pk},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_host_updated_log(log=log)

    def test_update_host(self):
        self.client.patch(
            path=reverse("host-details", kwargs={"host_id": self.host.pk}),
            data={
                "description": "Such wow new description",
                "fqdn": "new-test-fqdn",
            },
            content_type=APPLICATION_JSON,
        )
        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated_log(
            log=log,
            operation_name="Host updated",
            audit_object_name="new-test-fqdn",
            object_changes={
                "current": {"description": "Such wow new description", "fqdn": "new-test-fqdn"},
                "previous": {"description": "", "fqdn": "test-fqdn-2"},
            },
        )

        self.client.patch(
            path=reverse("host-details", kwargs={"host_id": self.host.pk}),
            data={"fqdn": "/*-/*-"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.check_host_updated_log(
            log=log,
            operation_name="Host updated",
            audit_object_name="new-test-fqdn",
            operation_result=AuditLogOperationResult.Fail,
        )

    def test_update_and_restore_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse("config-history", kwargs={"host_id": self.host.pk}),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_host_updated_log(log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user)

        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    "config-history-version-restore",
                    kwargs={"host_id": self.host.pk, "version": 1},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_host_updated_log(log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user)

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

        self.check_host_updated_log(log=log)

        response: Response = self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={
                    "provider_id": self.provider.pk,
                    "host_id": self.host.pk,
                    "version": self.config_log.pk,
                },
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_host_updated_log(log=log)

    def test_update_and_restore_via_provider_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(
                    "config-history",
                    kwargs={"provider_id": self.provider.pk, "host_id": self.host.pk},
                ),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_host_updated_log(log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user)

        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    "config-history-version-restore",
                    kwargs={"provider_id": self.provider.pk, "host_id": self.host.pk, "version": 1},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_host_updated_log(log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user)

    def test_action_launch(self):
        action = Action.objects.create(
            display_name=self.action_display_name,
            prototype=self.host_prototype,
            type="job",
            state_available="any",
        )
        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(path=reverse("run-task", kwargs={"host_id": self.host.pk, "action_id": action.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    "run-task",
                    kwargs={
                        "provider_id": self.provider.pk,
                        "host_id": self.host.pk,
                        "action_id": action.pk,
                    },
                )
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)

        self.host.cluster = self.cluster
        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    "run-task",
                    kwargs={
                        "cluster_id": self.host.cluster.pk,
                        "host_id": self.host.pk,
                        "action_id": action.pk,
                    },
                )
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)

    def test_change_maintenance_mode(self):
        self.client.post(
            path=reverse("host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated_log(log=log, operation_name="Host updated")

    def test_change_maintenance_mode_via_cluster(self):
        self.client.post(
            path=reverse(
                "host-maintenance-mode",
                kwargs={"cluster_id": self.cluster.pk, "host_id": self.host.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated_log(log=log, operation_name="Host updated")

    def test_change_maintenance_mode_via_provider(self):
        self.client.post(
            path=reverse(
                "host-maintenance-mode",
                kwargs={"provider_id": self.provider.pk, "host_id": self.host.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated_log(log=log, operation_name="Host updated")

    def test_change_maintenance_mode_failed(self):
        self.client.post(
            path=reverse("host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": MaintenanceMode.CHANGING},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated_log(
            log=log, operation_result=AuditLogOperationResult.Fail, operation_name="Host updated"
        )

    def test_change_maintenance_mode_denied(self):
        with self.no_rights_user_logged_in:
            self.client.post(
                path=reverse("host-maintenance-mode", kwargs={"host_id": self.host.pk}),
                data={"maintenance_mode": MaintenanceMode.ON},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_host_updated_log(
            log=log,
            operation_result=AuditLogOperationResult.Denied,
            operation_name="Host updated",
            user=self.no_rights_user,
        )
