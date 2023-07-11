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
    MaintenanceMode,
    ObjectConfig,
    Prototype,
    PrototypeExport,
    PrototypeImport,
)
from django.conf import settings
from django.urls import reverse
from rbac.models import Policy, Role, User
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestServiceAudit(BaseTestCase):
    # pylint: disable=too-many-instance-attributes,too-many-public-methods

    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        self.cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster")
        self.service_prototype = Prototype.objects.create(
            bundle=bundle,
            type="service",
            display_name="test_service",
        )
        config = ObjectConfig.objects.create(current=0, previous=0)
        self.config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = self.config_log.pk
        config.save(update_fields=["current"])

        self.service = ClusterObject.objects.create(
            prototype=self.service_prototype,
            cluster=self.cluster,
            config=config,
        )
        self.service_conf_updated_str = "Service configuration updated"
        self.action_display_name = "test_service_action"
        self.action = Action.objects.create(
            display_name="test_service_action",
            prototype=self.service_prototype,
            type="job",
            state_available="any",
        )

    def check_log(
        self,
        log: AuditLog,
        obj,
        obj_name: str,
        operation_name: str,
        object_type: AuditObjectType,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
        object_changes: dict | None = None,
    ):
        if object_changes is None:
            object_changes = {}

        self.assertEqual(log.audit_object.object_id, obj.pk)
        self.assertEqual(log.audit_object.object_name, obj_name)
        self.assertEqual(log.audit_object.object_type, object_type)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, user.username)
        self.assertEqual(log.object_changes, object_changes)

    def check_action_log(self, log: AuditLog) -> None:
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=f"{self.action_display_name} action launched",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_create(self):
        cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_2")
        self.client.post(
            path=reverse(viewname="v1:service"),
            data={
                "cluster_id": cluster.pk,
                "prototype_id": self.service_prototype.pk,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=cluster,
            obj_name=cluster.name,
            object_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.service_prototype.display_name} service added",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

        self.client.post(
            path=reverse(viewname="v1:service"),
            data={
                "cluster_id": cluster.pk,
                "prototype_id": self.service_prototype.pk,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=cluster,
            obj_name=cluster.name,
            object_type=AuditObjectType.CLUSTER,
            operation_name="service added",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.test_user,
        )

    def get_service_and_cluster(self) -> tuple[ClusterObject, Cluster]:
        bundle = Bundle.objects.create(name="test_bundle_2")
        cluster_prototype = Prototype.objects.create(
            bundle=bundle,
            type="cluster",
            name="Export_cluster",
        )
        service_prototype = Prototype.objects.create(
            bundle=bundle,
            type="service",
            name="Export_service",
            display_name="Export service",
        )
        cluster = Cluster.objects.create(prototype=cluster_prototype, name="Export cluster")
        PrototypeExport.objects.create(prototype=cluster_prototype, name="Export_cluster")
        service = ClusterObject.objects.create(prototype=service_prototype, cluster=cluster)
        PrototypeExport.objects.create(prototype=service_prototype, name="Export_service")
        PrototypeImport.objects.create(prototype=self.service_prototype, name="Export_cluster")
        PrototypeImport.objects.create(prototype=self.service_prototype, name="Export_service")

        return service, cluster

    def test_update_config(self):
        self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"service_id": self.service.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_update_config_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:config-history", kwargs={"service_id": self.service.pk}),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_restore_config(self):
        self.client.patch(
            path=reverse(
                viewname="v1:config-history-version-restore",
                kwargs={"service_id": self.service.pk, "version": self.config_log.pk},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_restore_config_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    viewname="v1:config-history-version-restore",
                    kwargs={"service_id": self.service.pk, "version": 1},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_delete(self):
        self.client.delete(
            path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service.cluster,
            obj_name=self.service.cluster.name,
            object_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.service.display_name} service removed",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

        response: Response = self.client.delete(
            path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(log.operation_name, "service removed")
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.FAIL)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.test_user.username)
        self.assertEqual(log.object_changes, {})

        self.assertFalse(log.audit_object)

    def test_delete_denied(self):
        role = Role.objects.get(name="View service config")
        policy = Policy.objects.create(name="test_policy", role=role)
        policy.user.add(self.no_rights_user)
        policy.add_object(self.service)
        policy.apply()

        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service.cluster,
            obj_name=self.service.cluster.name,
            object_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.service.display_name} service removed",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_delete_new(self):
        role = Role.objects.get(name="View service configurations")
        bundle_filename = "import.tar"
        with open(
            Path(settings.BASE_DIR, "python/audit/tests/files", bundle_filename),
            encoding=settings.ENCODING_UTF_8,
        ) as f:
            self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": bundle_filename},
        )

        response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={
                "name": "Cluster name",
                "prototype_id": Prototype.objects.get(name="importer_cluster").pk,
            },
        )

        cluster = Cluster.objects.get(pk=response.data["id"])
        response: Response = self.client.post(
            path=reverse(viewname="v1:service"),
            data={
                "cluster_id": response.data["id"],
                "prototype_id": Prototype.objects.get(name="importer_service").pk,
            },
            content_type=APPLICATION_JSON,
        )

        service = ClusterObject.objects.get(pk=response.data["id"])
        username = "new_user"
        password = self.get_random_str_num(length=12)
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-list"),
            data={
                "username": username,
                "password": password,
                "first_name": "aaa",
                "last_name": "aaa",
                "email": "aa@aa.ru",
                "group": [],
            },
        )

        user = User.objects.get(pk=response.data["id"])
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:role-list"),
            data={
                "display_name": "rolename",
                "type": "role",
                "category": [],
                "parametrized_by_type": [],
                "child": [{"id": role.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        created_role = Role.objects.get(pk=response.data["id"])
        self.client.post(
            path=reverse(viewname="v1:rbac:policy-list"),
            data={
                "name": "policy_name",
                "role": {"id": created_role.pk},
                "user": [{"id": user.pk}],
                "group": [],
                "object": [{"name": service.name, "type": "service", "id": service.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        with self.another_user_logged_in(username=username, password=password):
            response: Response = self.client.delete(
                path=reverse(viewname="v1:service-details", kwargs={"service_id": service.pk}),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=cluster,
            obj_name=cluster.name,
            object_type=AuditObjectType.CLUSTER,
            operation_name=f"{service.display_name} service removed",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=user,
        )

    def test_import(self):
        self.client.post(
            path=reverse(viewname="v1:service-import", kwargs={"service_id": self.service.pk}),
            data={"bind": []},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name="Service import updated",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_import_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:service-import", kwargs={"service_id": self.service.pk}),
                data={"bind": []},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name="Service import updated",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_bind_unbind_cluster_to_service(self):
        _, cluster = self.get_service_and_cluster()
        self.client.post(
            path=reverse(viewname="v1:service-bind", kwargs={"service_id": self.service.pk}),
            data={"export_cluster_id": cluster.pk},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=f"Service bound to {cluster.name}",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

        bind = ClusterBind.objects.first()
        self.client.delete(
            path=reverse(
                viewname="v1:service-bind-details", kwargs={"service_id": self.service.pk, "bind_id": bind.pk}
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=f"{cluster.name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_bind_unbind_service_to_service(self):
        service, cluster = self.get_service_and_cluster()
        self.client.post(
            path=reverse(viewname="v1:service-bind", kwargs={"service_id": self.service.pk}),
            data={"export_cluster_id": cluster.pk, "export_service_id": service.pk},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=f"Service bound to {cluster.name}/{service.display_name}",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

        bind = ClusterBind.objects.first()
        self.client.delete(
            path=reverse(
                viewname="v1:service-bind-details", kwargs={"service_id": self.service.pk, "bind_id": bind.pk}
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=f"{cluster.name}/{service.display_name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_bind_unbind_denied(self):
        _, cluster = self.get_service_and_cluster()
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:service-bind", kwargs={"service_id": self.service.pk}),
                data={"export_cluster_id": cluster.pk},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=f"Service bound to {cluster.name}",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

        self.client.post(
            path=reverse(viewname="v1:service-bind", kwargs={"service_id": self.service.pk}),
            data={"export_cluster_id": cluster.pk},
            content_type=APPLICATION_JSON,
        )
        bind = ClusterBind.objects.first()
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(
                    viewname="v1:service-bind-details",
                    kwargs={"service_id": self.service.pk, "bind_id": bind.pk},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            object_type=AuditObjectType.SERVICE,
            operation_name=f"{cluster.name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_action_launch(self):
        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    viewname="v1:run-task", kwargs={"service_id": self.service.pk, "action_id": self.action.pk}
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(
                    viewname="v1:run-task",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service.pk,
                        "action_id": self.action.pk,
                    },
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(log=log)

    def test_change_maintenance_mode(self):
        self.client.post(
            path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            operation_name="Service updated",
            object_type=AuditObjectType.SERVICE,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            object_changes={"current": {"maintenance_mode": "ON"}, "previous": {"maintenance_mode": "OFF"}},
        )

    def test_change_maintenance_mode_via_cluster(self):
        self.client.post(
            path=reverse(
                viewname="v1:service-maintenance-mode",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            operation_name="Service updated",
            object_type=AuditObjectType.SERVICE,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            object_changes={"current": {"maintenance_mode": "ON"}, "previous": {"maintenance_mode": "OFF"}},
        )

    def test_change_maintenance_mode_failed(self):
        self.client.post(
            path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": MaintenanceMode.CHANGING},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            operation_name="Service updated",
            object_type=AuditObjectType.SERVICE,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.test_user,
        )

    def test_change_maintenance_mode_denied(self):
        with self.no_rights_user_logged_in:
            self.client.post(
                path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
                data={"maintenance_mode": MaintenanceMode.ON},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            operation_name="Service updated",
            object_type=AuditObjectType.SERVICE,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )
