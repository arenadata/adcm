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
    ClusterObject,
    ConfigLog,
    GroupConfig,
    Host,
    ObjectConfig,
    Prototype,
    ServiceComponent,
)
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestGroupConfig(BaseTestCase):
    # pylint: disable=too-many-public-methods
    def setUp(self) -> None:
        super().setUp()

        self.config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=self.config, config="{}")
        self.bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=self.bundle)
        self.cluster = Cluster.objects.create(
            prototype=prototype,
            config=self.config,
            name="test_cluster",
        )
        self.name = "test_group_config"
        self.group_config = GroupConfig.objects.create(
            name="test_group_config_2",
            object_id=self.cluster.pk,
            object_type=ContentType.objects.get(app_label="cm", model="cluster"),
            config_id=self.config.pk,
        )
        self.host = Host.objects.create(
            fqdn="test_host_fqdn", prototype=prototype, cluster=self.cluster
        )
        self.created_operation_name = "test_group_config configuration group created"

    def create_group_config(
        self,
        name: str,
        object_id: int,
        object_type: str,
        config_id: int,
    ) -> Response:
        return self.client.post(
            path=reverse("group-config-list"),
            data={
                "name": name,
                "object_id": object_id,
                "object_type": object_type,
                "config_id": config_id,
            },
        )

    def get_service(self):
        return ClusterObject.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type="service"),
            cluster=self.cluster,
            config=self.config,
        )

    def get_component(self):
        return ServiceComponent.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type="component"),
            cluster=self.cluster,
            service=ClusterObject.objects.create(
                prototype=Prototype.objects.create(bundle=self.bundle, type="service"),
                cluster=self.cluster,
                config=self.config,
            ),
            config=self.config,
        )

    def check_log(  # pylint: disable=too-many-arguments
        self,
        log: AuditLog,
        obj,
        obj_type: AuditObjectType,
        operation_name: str,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
    ) -> None:
        assert log.audit_object.object_id == obj.pk
        assert log.audit_object.object_name == obj.name
        assert log.audit_object.object_type == obj_type
        assert not log.audit_object.is_deleted
        assert log.operation_name == operation_name
        assert log.operation_type == operation_type
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

    def check_log_denied(self, log: AuditLog) -> None:
        assert not log.audit_object
        assert log.operation_name == "configuration group created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Denied
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.no_rights_user.pk
        assert isinstance(log.object_changes, dict)

    def check_log_updated(
        self, log: AuditLog, operation_result: AuditLogOperationResult, user: User
    ) -> None:
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_type=AuditObjectType.Cluster,
            operation_name=f"{self.group_config.name} configuration group updated",
            operation_type=AuditLogOperationType.Update,
            operation_result=operation_result,
            user=user,
        )

    def test_create_for_cluster(self):
        self.create_group_config(
            name=self.name,
            object_id=self.cluster.pk,
            object_type=AuditObjectType.Cluster,
            config_id=self.config.pk,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_type=AuditObjectType.Cluster,
            operation_name=self.created_operation_name,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_create_for_cluster_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.create_group_config(
                name=self.name,
                object_id=self.cluster.pk,
                object_type=AuditObjectType.Cluster,
                config_id=self.config.pk,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_denied(log=log)

    def test_create_for_service(self):
        service = self.get_service()
        self.create_group_config(
            name=self.name,
            object_id=service.pk,
            object_type=AuditObjectType.Service,
            config_id=self.config.pk,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=service,
            obj_type=AuditObjectType.Service,
            operation_name=self.created_operation_name,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_create_for_service_denied(self):
        service = self.get_service()
        with self.no_rights_user_logged_in:
            res: Response = self.create_group_config(
                name=self.name,
                object_id=service.pk,
                object_type=AuditObjectType.Service,
                config_id=self.config.pk,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_denied(log=log)

    def test_create_for_component(self):
        component = self.get_component()
        self.create_group_config(
            name=self.name,
            object_id=component.pk,
            object_type=AuditObjectType.Component,
            config_id=self.config.pk,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=component,
            obj_type=AuditObjectType.Component,
            operation_name=self.created_operation_name,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_create_for_component_denied(self):
        component = self.get_component()
        with self.no_rights_user_logged_in:
            res: Response = self.create_group_config(
                name=self.name,
                object_id=component.pk,
                object_type=AuditObjectType.Component,
                config_id=self.config.pk,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_denied(log=log)

    def test_delete(self):
        self.client.delete(path=reverse("group-config-detail", kwargs={"pk": self.group_config.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_type=AuditObjectType.Cluster,
            operation_name=f"{self.group_config.name} configuration group deleted",
            operation_type=AuditLogOperationType.Delete,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=reverse("group-config-detail", kwargs={"pk": self.group_config.pk})
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_type=AuditObjectType.Cluster,
            operation_name=f"{self.group_config.name} configuration group deleted",
            operation_type=AuditLogOperationType.Delete,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_update_put(self):
        self.client.put(
            path=f"/api/v1/group-config/{self.group_config.pk}/",
            data={
                "name": self.group_config.name,
                "object_id": self.cluster.pk,
                "object_type": "cluster",
                "config_id": self.config.id,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_updated(
            log=log,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_update_put_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.put(
                path=f"/api/v1/group-config/{self.group_config.pk}/",
                data={
                    "name": self.group_config.name,
                    "object_id": self.cluster.pk,
                    "object_type": "cluster",
                    "config_id": self.config.id,
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_updated(
            log=log,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_update_patch(self):
        self.client.patch(
            path=f"/api/v1/group-config/{self.group_config.pk}/",
            data={
                "name": self.group_config.name,
                "object_id": self.cluster.pk,
                "object_type": "cluster",
                "config_id": self.config.id,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_updated(
            log=log,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_update_patch_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.patch(
                path=f"/api/v1/group-config/{self.group_config.pk}/",
                data={
                    "name": self.group_config.name,
                    "object_id": self.cluster.pk,
                    "object_type": "cluster",
                    "config_id": self.config.id,
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_updated(
            log=log,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_add_remove_host(self):
        self.client.post(
            path=f"/api/v1/group-config/{self.group_config.pk}/host/",
            data={"id": self.host.id},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_type=AuditObjectType.Cluster,
            operation_name=f"{self.host.fqdn} host added to "
            f"{self.group_config.name} configuration group",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

        self.client.delete(
            path=f"/api/v1/group-config/{self.group_config.pk}/host/{self.host.id}/",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_type=AuditObjectType.Cluster,
            operation_name=f"{self.host.fqdn} host removed from "
            f"{self.group_config.name} configuration group",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_add_remove_host_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=f"/api/v1/group-config/{self.group_config.pk}/host/",
                data={"id": self.host.id},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_type=AuditObjectType.Cluster,
            operation_name=f"{self.host.fqdn} host added to "
            f"{self.group_config.name} configuration group",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

        res: Response = self.client.post(
            path=f"/api/v1/group-config/{self.group_config.pk}/host/",
            data={"id": self.host.id},
        )

        assert res.status_code == HTTP_201_CREATED

        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=f"/api/v1/group-config/{self.group_config.pk}/host/{self.host.id}/",
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_type=AuditObjectType.Cluster,
            operation_name=f"{self.host.fqdn} host removed from "
            f"{self.group_config.name} configuration group",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )
