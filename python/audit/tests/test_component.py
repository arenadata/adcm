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
from unittest.mock import patch

from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_403_FORBIDDEN

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
    ClusterObject,
    ConfigLog,
    MaintenanceMode,
    ObjectConfig,
    Prototype,
    ServiceComponent,
)
from rbac.models import User


class TestComponent(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster = Cluster.objects.create(prototype=cluster_prototype, name="test_cluster")
        service_prototype = Prototype.objects.create(
            bundle=bundle,
            type="service",
            display_name="test_service",
        )
        self.service = ClusterObject.objects.create(prototype=service_prototype, cluster=self.cluster)
        self.component_prototype = Prototype.objects.create(
            bundle=bundle,
            type="component",
            display_name="test_component",
        )
        config = ObjectConfig.objects.create(current=0, previous=0)
        self.config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = self.config_log.pk
        config.save(update_fields=["current"])

        self.component = ServiceComponent.objects.create(
            prototype=self.component_prototype,
            cluster=self.cluster,
            service=self.service,
            config=config,
        )
        self.action_display_name = "test_component_action"
        self.api_create_str = "api.action.views.create"

    def check_log(
        self,
        log: AuditLog,
        operation_result: AuditLogOperationResult = AuditLogOperationResult.Success,
        user: User | None = None,
        operation_name: str = "Component configuration updated",
    ):
        if user is None:
            user = self.test_user

        self.assertEqual(log.audit_object.object_id, self.component.pk)
        self.assertEqual(
            log.audit_object.object_name,
            f"{self.cluster.name}/{self.service.display_name}/{self.component.display_name}",
        )
        self.assertEqual(log.audit_object.object_type, AuditObjectType.Component)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.Update)
        self.assertEqual(log.operation_result, operation_result)
        self.assertEqual(log.user.pk, user.pk)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.object_changes, {})

    def check_action_log(self, log: AuditLog) -> None:
        self.assertEqual(log.audit_object.object_id, self.component.pk)
        self.assertEqual(
            log.audit_object.object_name,
            f"{self.cluster.name}/{self.service.display_name}/{self.component.display_name}",
        )
        self.assertEqual(log.audit_object.object_type, AuditObjectType.Component)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, f"{self.action_display_name} action launched")
        self.assertEqual(log.operation_type, AuditLogOperationType.Update)
        self.assertEqual(log.operation_result, AuditLogOperationResult.Success)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.object_changes, {})

    def test_update_config(self):
        self.client.post(
            path=reverse("config-history", kwargs={"component_id": self.component.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(log=log)

    def test_restore_config(self):
        self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={"component_id": self.component.pk, "version": self.config_log.pk},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(log)

    def test_restore_config_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    "config-history-version-restore",
                    kwargs={"component_id": self.component.pk, "version": self.config_log.pk},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_update_config_via_service(self):
        self.client.post(
            path=reverse(
                "config-history",
                kwargs={"service_id": self.service.pk, "component_id": self.component.pk},
            ),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(log)

    def test_update_config_via_service_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(
                    "config-history",
                    kwargs={"service_id": self.service.pk, "component_id": self.component.pk},
                ),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_restore_config_via_service(self):
        self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={
                    "service_id": self.service.pk,
                    "component_id": self.component.pk,
                    "version": self.config_log.pk,
                },
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(log)

    def test_restore_config_via_service_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    "config-history-version-restore",
                    kwargs={
                        "service_id": self.service.pk,
                        "component_id": self.component.pk,
                        "version": self.config_log.pk,
                    },
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_action_launch(self):
        action = Action.objects.create(
            display_name=self.action_display_name,
            prototype=self.component_prototype,
            type="job",
            state_available="any",
        )
        with patch(self.api_create_str, return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    "run-task",
                    kwargs={
                        "component_id": self.component.pk,
                        "action_id": action.pk,
                    },
                )
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)

        with patch(self.api_create_str, return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    "run-task",
                    kwargs={
                        "service_id": self.service.pk,
                        "component_id": self.component.pk,
                        "action_id": action.pk,
                    },
                )
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)

        with patch(self.api_create_str, return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    "run-task",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service.pk,
                        "component_id": self.component.pk,
                        "action_id": action.pk,
                    },
                )
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)

    def test_change_maintenance_mode(self):
        self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Component updated",
        )

    def test_change_maintenance_mode_via_service(self):
        self.client.post(
            path=reverse(
                "component-maintenance-mode",
                kwargs={"service_id": self.service.pk, "component_id": self.component.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Component updated",
        )

    def test_change_maintenance_mode_via_cluster(self):
        self.client.post(
            path=reverse(
                "component-maintenance-mode",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.service.pk,
                    "component_id": self.component.pk,
                },
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Component updated",
        )

    def test_change_maintenance_mode_failed(self):
        self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": MaintenanceMode.CHANGING},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Component updated",
            operation_result=AuditLogOperationResult.Fail,
        )

    def test_change_maintenance_mode_denied(self):
        with self.no_rights_user_logged_in:
            self.client.post(
                path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
                data={"maintenance_mode": MaintenanceMode.ON},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Component updated",
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )
