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
    ClusterBind,
    ClusterObject,
    ConfigLog,
    ObjectConfig,
    Prototype,
    PrototypeExport,
    PrototypeImport,
)
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestService(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        self.cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster")
        service_prototype = Prototype.objects.create(bundle=bundle, type="service")
        config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.service = ClusterObject.objects.create(
            prototype=service_prototype, cluster=self.cluster, config=config
        )
        self.service_conf_updated_str = "Service configuration updated"
        self.action_display_name = "test_service_action"
        self.action = Action.objects.create(
            display_name="test_service_action",
            prototype=service_prototype,
            type="job",
            state_available="any",
        )

    def check_log(  # pylint: disable=too-many-arguments
        self,
        log: AuditLog,
        obj,
        operation_name: str,
        object_type: AuditObjectType,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
    ):
        self.assertEqual(log.audit_object.object_id, obj.pk)
        self.assertEqual(log.audit_object.object_name, obj.name)
        self.assertEqual(log.audit_object.object_type, object_type)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, {})

    def check_action_log(self, log: AuditLog) -> None:
        self.check_log(
            log=log,
            obj=self.service,
            object_type=AuditObjectType.Service,
            operation_name=f"{self.action_display_name} action launched",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    @staticmethod
    def get_service_and_cluster() -> tuple[ClusterObject, Cluster]:
        bundle = Bundle.objects.create(name="test_bundle_2")
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        service_prototype = Prototype.objects.create(bundle=bundle, type="service")
        cluster = Cluster.objects.create(prototype=cluster_prototype, name="test_cluster_2")
        PrototypeExport.objects.create(prototype=cluster_prototype)
        service = ClusterObject.objects.create(prototype=service_prototype, cluster=cluster)
        PrototypeImport.objects.create(prototype=service_prototype)

        return service, cluster

    def test_update(self):
        self.client.post(
            path=reverse("config-history", kwargs={"service_id": self.service.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            object_type=AuditObjectType.Service,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_update_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse("config-history", kwargs={"service_id": self.service.pk}),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.service,
            object_type=AuditObjectType.Service,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_restore(self):
        self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={"service_id": self.service.pk, "version": 1},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            object_type=AuditObjectType.Service,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_restore_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.patch(
                path=reverse(
                    "config-history-version-restore",
                    kwargs={"service_id": self.service.pk, "version": 1},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.service,
            object_type=AuditObjectType.Service,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_delete(self):
        self.client.delete(
            path=reverse("service-details", kwargs={"service_id": self.service.pk}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service.cluster,
            object_type=AuditObjectType.Cluster,
            operation_name=f"{self.service.display_name} service removed",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=reverse("service-details", kwargs={"service_id": self.service.pk}),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service.cluster,
            object_type=AuditObjectType.Cluster,
            operation_name=f"{self.service.display_name} service removed",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_import(self):
        self.client.post(
            path=reverse("service-import", kwargs={"service_id": self.service.pk}),
            data={"bind": []},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            object_type=AuditObjectType.Service,
            operation_name="Service import updated",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_import_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse("service-import", kwargs={"service_id": self.service.pk}),
                data={"bind": []},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service,
            object_type=AuditObjectType.Service,
            operation_name="Service import updated",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_bind_unbind(self):
        service, cluster = self.get_service_and_cluster()
        self.client.post(
            path=reverse("service-bind", kwargs={"service_id": service.pk}),
            data={"export_cluster_id": cluster.pk},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=service,
            object_type=AuditObjectType.Service,
            operation_name='Service bound to test_cluster_2/service #2 ""',
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

        bind = ClusterBind.objects.first()
        self.client.delete(
            path=reverse(
                "service-bind-details", kwargs={"service_id": service.pk, "bind_id": bind.pk}
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=service,
            object_type=AuditObjectType.Service,
            operation_name='test_cluster_2/service #2 "" unbound',
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

        res: Response = self.client.delete(
            path=reverse(
                "service-bind-details", kwargs={"service_id": service.pk, "bind_id": bind.pk}
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=service,
            object_type=AuditObjectType.Service,
            operation_name=f"/{str(service)} unbound",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Fail,
            user=self.test_user,
        )

    def test_bind_unbind_denied(self):
        service, cluster = self.get_service_and_cluster()
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse("service-bind", kwargs={"service_id": service.pk}),
                data={"export_cluster_id": cluster.pk},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=service,
            object_type=AuditObjectType.Service,
            operation_name='Service bound to test_cluster_2/service #2 ""',
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

        self.client.post(
            path=reverse("service-bind", kwargs={"service_id": service.pk}),
            data={"export_cluster_id": cluster.pk},
            content_type=APPLICATION_JSON,
        )
        bind = ClusterBind.objects.first()
        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=reverse(
                    "service-bind-details", kwargs={"service_id": service.pk, "bind_id": bind.pk}
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=service,
            object_type=AuditObjectType.Service,
            operation_name='test_cluster_2/service #2 "" unbound',
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_action_launch(self):
        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    "run-task", kwargs={"service_id": self.service.pk, "action_id": self.action.pk}
                )
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    "run-task",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service.pk,
                        "action_id": self.action.pk,
                    },
                )
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)
