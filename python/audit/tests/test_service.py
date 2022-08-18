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
from cm.models import (
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
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestService(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        self.cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster")
        service_prototype = Prototype.objects.create(bundle=bundle, type="service")
        config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.service = ClusterObject.objects.create(
            prototype=service_prototype, cluster=cluster, config=config
        )
        self.service_conf_updated_str = "Service configuration updated"

    @staticmethod
    def check_log(
        log: AuditLog,
        obj,
        operation_name: str,
        object_type: AuditObjectType,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
    ):
        assert log.audit_object.object_id == obj.pk
        assert log.audit_object.object_name == obj.name
        assert log.audit_object.object_type == object_type
        assert not log.audit_object.is_deleted
        assert log.operation_name == operation_name
        assert log.operation_type == operation_type
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

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
            path=f"/api/v1/service/{self.service.pk}/config/history/",
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
                path=f"/api/v1/service/{self.service.pk}/config/history/",
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
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
            path=f"/api/v1/service/{self.service.pk}/config/history/1/restore/",
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
                path=f"/api/v1/service/{self.service.pk}/config/history/1/restore/",
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
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
            path=f"/api/v1/service/{self.service.pk}/",
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
                path=f"/api/v1/service/{self.service.pk}/",
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_404_NOT_FOUND
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
            path=f"/api/v1/service/{self.service.pk}/import/",
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
                path=f"/api/v1/service/{self.service.pk}/import/",
                data={"bind": []},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_404_NOT_FOUND
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
            path=f"/api/v1/service/{service.pk}/bind/",
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
            path=f"/api/v1/service/{service.pk}/bind/{bind.pk}/",
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

    def test_bind_unbind_denied(self):
        service, cluster = self.get_service_and_cluster()
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=f"/api/v1/service/{service.pk}/bind/",
                data={"export_cluster_id": cluster.pk},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_404_NOT_FOUND
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
            path=f"/api/v1/service/{service.pk}/bind/",
            data={"export_cluster_id": cluster.pk},
            content_type=APPLICATION_JSON,
        )
        bind = ClusterBind.objects.first()
        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=f"/api/v1/service/{service.pk}/bind/{bind.pk}/",
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_404_NOT_FOUND
        self.check_log(
            log=log,
            obj=service,
            object_type=AuditObjectType.Service,
            operation_name='test_cluster_2/service #2 "" unbound',
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )
