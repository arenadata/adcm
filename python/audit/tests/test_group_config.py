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
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestGroupConfig(BaseTestCase):
    # pylint: disable=too-many-public-methods,too-many-instance-attributes

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
        self.conf_group_created_str = "configuration group created"
        self.created_operation_name = f"{self.name} {self.conf_group_created_str}"

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
        self.assertEqual(log.audit_object.object_id, obj.pk)
        self.assertEqual(log.audit_object.object_name, obj.name)
        self.assertEqual(log.audit_object.object_type, obj_type)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, {})

    def check_log_no_obj(
        self,
        log: AuditLog,
        operation_name: str,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
    ) -> None:
        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, {})

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

    def test_create_for_cluster_failed(self):
        res: Response = self.client.post(
            path=reverse("group-config-list"),
            data={
                "name": self.name,
                "object_type": AuditObjectType.Cluster,
                "config_id": self.config.pk,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_400_BAD_REQUEST)
        self.check_log_no_obj(
            log=log,
            operation_name=self.conf_group_created_str,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Fail,
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

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
        self.check_log_no_obj(
            log=log,
            operation_name=self.conf_group_created_str,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

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

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
        self.check_log_no_obj(
            log=log,
            operation_name=self.conf_group_created_str,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

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

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
        self.check_log_no_obj(
            log=log,
            operation_name=self.conf_group_created_str,
            operation_type=AuditLogOperationType.Create,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

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

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
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

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
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

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
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

    def test_add_host_failed(self):
        host_ids = Host.objects.all().values_list("pk", flat=True).order_by("-pk")
        res: Response = self.client.post(
            path=f"/api/v1/group-config/{self.group_config.pk}/host/",
            data={"id": host_ids[0] + 1},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_400_BAD_REQUEST)
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_type=AuditObjectType.Cluster,
            operation_name=f"host added to {self.group_config.name} configuration group",
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Fail,
            user=self.test_user,
        )

    def test_add_remove_host_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=f"/api/v1/group-config/{self.group_config.pk}/host/",
                data={"id": self.host.id},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
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

        self.assertEqual(res.status_code, HTTP_201_CREATED)

        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=f"/api/v1/group-config/{self.group_config.pk}/host/{self.host.id}/",
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)
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
