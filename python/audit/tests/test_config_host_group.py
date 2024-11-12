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
from pathlib import Path

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import (
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    ObjectConfig,
    Prototype,
    Service,
)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
)

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)


class TestCHGAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(obj_ref=self.config, config="{}")
        self.config.current = config_log.pk
        self.config.save(update_fields=["current"])

        self.bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=self.bundle)
        self.cluster = Cluster.objects.create(
            prototype=prototype,
            config=self.config,
            name="test_cluster",
        )
        self.name = "test_config_host_group"
        self.host_group = ConfigHostGroup.objects.create(
            name="test_config_host_group_2",
            object_id=self.cluster.pk,
            object_type=ContentType.objects.get(app_label="cm", model="cluster"),
            config_id=self.config.pk,
        )
        self.host = Host.objects.create(fqdn="test_host_fqdn", prototype=prototype, cluster=self.cluster)
        self.conf_group_created_str = "configuration group created"
        self.created_operation_name = f"{self.name} {self.conf_group_created_str}"

    def create_config_host_group(
        self,
        name: str,
        object_id: int,
        object_type: str,
        config_id: int,
    ) -> Response:
        return self.client.post(
            path=reverse(viewname="v1:group-config-list"),
            data={
                "name": name,
                "object_id": object_id,
                "object_type": object_type,
                "config_id": config_id,
            },
        )

    def get_service(self):
        return Service.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="service",
                display_name="test_service",
            ),
            cluster=self.cluster,
            config=self.config,
        )

    def get_component(self):
        return Component.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="component",
                display_name="test_component",
            ),
            cluster=self.cluster,
            service=Service.objects.create(
                prototype=Prototype.objects.create(bundle=self.bundle, type="service"),
                cluster=self.cluster,
                config=self.config,
            ),
            config=self.config,
        )

    def check_log(
        self,
        log: AuditLog,
        obj,
        obj_name: str,
        obj_type: AuditObjectType,
        operation_name: str,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
    ) -> None:
        self.assertEqual(log.audit_object.object_id, obj.pk)
        self.assertEqual(log.audit_object.object_name, obj_name)
        self.assertEqual(log.audit_object.object_type, obj_type)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, user.username)
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
        self.assertEqual(log.user.username, user.username)
        self.assertEqual(log.object_changes, {})

    def check_log_updated(self, log: AuditLog, operation_result: AuditLogOperationResult, user: User) -> None:
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.host_group.name} configuration group updated",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=operation_result,
            user=user,
        )

    def test_create_for_cluster(self):
        self.create_config_host_group(
            name=self.name,
            object_id=self.cluster.pk,
            object_type=AuditObjectType.CLUSTER,
            config_id=self.config.pk,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=self.created_operation_name,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_create_for_cluster_failed(self):
        response = self.client.post(
            path=reverse(viewname="v1:group-config-list"),
            data={
                "name": self.name,
                "object_type": AuditObjectType.CLUSTER,
                "config_id": self.config.pk,
            },
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_log_no_obj(
            log=log,
            operation_name=self.conf_group_created_str,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.test_user,
        )

    def test_create_for_cluster_denied(self):
        with self.no_rights_user_logged_in:
            response = self.create_config_host_group(
                name=self.name,
                object_id=self.cluster.pk,
                object_type=AuditObjectType.CLUSTER,
                config_id=self.config.pk,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_no_obj(
            log=log,
            operation_name=self.conf_group_created_str,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_create_for_service(self):
        service = self.get_service()
        self.create_config_host_group(
            name=self.name,
            object_id=service.pk,
            object_type=AuditObjectType.SERVICE,
            config_id=self.config.pk,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=service,
            obj_name=f"{self.cluster.name}/{service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=self.created_operation_name,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_create_for_service_denied(self):
        service = self.get_service()
        with self.no_rights_user_logged_in:
            response = self.create_config_host_group(
                name=self.name,
                object_id=service.pk,
                object_type=AuditObjectType.SERVICE,
                config_id=self.config.pk,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_no_obj(
            log=log,
            operation_name=self.conf_group_created_str,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_create_for_component(self):
        component = self.get_component()
        self.create_config_host_group(
            name=self.name,
            object_id=component.pk,
            object_type=AuditObjectType.COMPONENT,
            config_id=self.config.pk,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=component,
            obj_name=f"{self.cluster.name}/{component.service.display_name}" f"/{component.display_name}",
            obj_type=AuditObjectType.COMPONENT,
            operation_name=self.created_operation_name,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_create_for_component_denied(self):
        component = self.get_component()
        with self.no_rights_user_logged_in:
            response = self.create_config_host_group(
                name=self.name,
                object_id=component.pk,
                object_type=AuditObjectType.COMPONENT,
                config_id=self.config.pk,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_no_obj(
            log=log,
            operation_name=self.conf_group_created_str,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_delete(self):
        self.client.delete(path=reverse(viewname="v1:group-config-detail", kwargs={"pk": self.host_group.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.host_group.name} configuration group deleted",
            operation_type=AuditLogOperationType.DELETE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            response = self.client.delete(
                path=reverse(viewname="v1:group-config-detail", kwargs={"pk": self.host_group.pk}),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.host_group.name} configuration group deleted",
            operation_type=AuditLogOperationType.DELETE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_put(self):
        self.client.put(
            path=f"/api/v1/group-config/{self.host_group.pk}/",
            data={
                "name": self.host_group.name,
                "object_id": self.cluster.pk,
                "object_type": "cluster",
                "config_id": self.config.id,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_updated(
            log=log,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_update_put_denied(self):
        with self.no_rights_user_logged_in:
            response = self.client.put(
                path=f"/api/v1/group-config/{self.host_group.pk}/",
                data={
                    "name": self.host_group.name,
                    "object_id": self.cluster.pk,
                    "object_type": "cluster",
                    "config_id": self.config.id,
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_updated(
            log=log,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_patch(self):
        self.client.patch(
            path=f"/api/v1/group-config/{self.host_group.pk}/",
            data={
                "name": self.host_group.name,
                "object_id": self.cluster.pk,
                "object_type": "cluster",
                "config_id": self.config.id,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_updated(
            log=log,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_update_patch_denied(self):
        with self.no_rights_user_logged_in:
            response = self.client.patch(
                path=f"/api/v1/group-config/{self.host_group.pk}/",
                data={
                    "name": self.host_group.name,
                    "object_id": self.cluster.pk,
                    "object_type": "cluster",
                    "config_id": self.config.id,
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_updated(
            log=log,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_add_remove_host(self):
        self.client.post(
            path=f"/api/v1/group-config/{self.host_group.pk}/host/",
            data={"id": self.host.id},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.host.fqdn} host added to " f"{self.host_group.name} configuration group",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

        self.client.delete(
            path=f"/api/v1/group-config/{self.host_group.pk}/host/{self.host.id}/",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.host.fqdn} host removed from " f"{self.host_group.name} configuration group",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_add_host_failed(self):
        host_pks = Host.objects.all().values_list("pk", flat=True).order_by("-pk")
        response = self.client.post(
            path=f"/api/v1/group-config/{self.host_group.pk}/host/",
            data={"id": host_pks[0] + 1},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"host added to {self.host_group.name} configuration group",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.test_user,
        )

    def test_add_remove_host_denied(self):
        with self.no_rights_user_logged_in:
            response = self.client.post(
                path=f"/api/v1/group-config/{self.host_group.pk}/host/",
                data={"id": self.host.id},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.host.fqdn} host added to " f"{self.host_group.name} configuration group",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

        response = self.client.post(
            path=f"/api/v1/group-config/{self.host_group.pk}/host/",
            data={"id": self.host.id},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        with self.no_rights_user_logged_in:
            response = self.client.delete(
                path=f"/api/v1/group-config/{self.host_group.pk}/host/{self.host.id}/",
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.host.fqdn} host removed from " f"{self.host_group.name} configuration group",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )


class TestCHGOperationName(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster = None
        self.config_id = None
        self.host_group_id = None
        self.host_group = None

    def check_log(self, log: AuditLog, operation_result: AuditLogOperationResult, user: User):
        self.assertEqual(log.audit_object.object_id, self.cluster.pk)
        self.assertEqual(log.audit_object.object_name, self.cluster.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.CLUSTER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(
            log.operation_name,
            f"{self.host_group.name} configuration group {AuditLogOperationType.UPDATE}d",
        )
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, user.username)
        self.assertEqual(log.object_changes, {})

    def create_cluster_from_bundle(self):
        test_bundle_filename = "group-config.tar"
        test_bundle_path = Path(
            self.base_dir,
            "python/audit/tests/files",
            test_bundle_filename,
        )
        with open(test_bundle_path, encoding=settings.ENCODING_UTF_8) as f:
            response = self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": test_bundle_filename},
        )
        bundle_id = response.data["id"]
        prototype_id = Prototype.objects.get(bundle_id=bundle_id, type="cluster").pk

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={
                "prototype_id": prototype_id,
                "name": "Magnificent Zambezi",
                "display_name": "cluster_for_updates",
                "bundle_id": bundle_id,
            },
        )
        cluster_id = response.data["id"]
        self.cluster = Cluster.objects.get(pk=cluster_id)

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.post(
            path=reverse(viewname="v1:group-config-list"),
            data={"name": "groupname", "object_type": "cluster", "object_id": cluster_id},
        )
        self.host_group_id = response.data["id"]
        self.config_id = response.data["config_id"]
        self.host_group = ConfigHostGroup.objects.get(pk=self.host_group_id)

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_config_host_group_operation_name(self):
        self.create_cluster_from_bundle()
        response = self.client.post(
            path=f"/api/v1/group-config/{self.host_group_id}/config/{self.config_id}/config-log/",
            data={
                "config": {"param_1": "aaa", "param_2": None, "param_3": None},
                "attr": {
                    "group_keys": {"param_1": True, "param_2": False, "param_3": False},
                    "custom_group_keys": {"param_1": True, "param_2": True, "param_3": True},
                },
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_log(log=log, operation_result=AuditLogOperationResult.SUCCESS, user=self.test_user)

    def test_config_host_group_operation_name_denied(self):
        self.create_cluster_from_bundle()
        with self.no_rights_user_logged_in:
            response = self.client.post(
                path=f"/api/v1/group-config/{self.host_group_id}" f"/config/{self.config_id}/config-log/",
                data={
                    "config": {"param_1": "aaa", "param_2": None, "param_3": None},
                    "attr": {
                        "group_keys": {"param_1": True, "param_2": False, "param_3": False},
                        "custom_group_keys": {"param_1": True, "param_2": True, "param_3": True},
                    },
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(log=log, operation_result=AuditLogOperationResult.DENIED, user=self.no_rights_user)

    def test_config_host_group_operation_name_failed(self):
        self.create_cluster_from_bundle()
        response = self.client.post(
            path=f"/api/v1/group-config/{self.host_group_id}/config/{self.config_id}/config-log/",
            data={
                "config": {"param_1": "wrong", "param_2": None, "param_3": 5.0},
                "attr": {
                    "group_keys": {"param_1": False, "param_2": False, "param_3": False},
                    "custom_group_keys": {"param_1": True, "param_2": True, "param_3": True},
                },
            },
            content_type=APPLICATION_JSON,
        )

        log = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_log(log=log, operation_result=AuditLogOperationResult.FAIL, user=self.test_user)
