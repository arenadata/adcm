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

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import (
    Action,
    Bundle,
    Cluster,
    ClusterBind,
    Component,
    ConfigLog,
    Host,
    HostComponent,
    ObjectConfig,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    Provider,
    Service,
    Upgrade,
)
from django.conf import settings
from django.urls import reverse
from rbac.models import Policy, Role, User
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
)


class TestClusterAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.test_cluster_name = "test-cluster"
        self.description = "Such wow new description"
        self.cluster_prototype = Prototype.objects.create(bundle=self.bundle, type="cluster")

        config = ObjectConfig.objects.create(current=0, previous=0)
        self.config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = self.config_log.pk
        config.save(update_fields=["current"])

        self.cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_2", config=config)
        self.service_prototype = Prototype.objects.create(
            bundle=self.bundle,
            type="service",
            display_name="test_service",
        )
        self.service = Service.objects.create(
            prototype=self.service_prototype,
            cluster=self.cluster,
        )

        provider_prototype = Prototype.objects.create(bundle=self.bundle, type="provider")
        provider = Provider.objects.create(
            name="test_provider",
            prototype=provider_prototype,
        )
        host_prototype = Prototype.objects.create(bundle=self.bundle, type="host")
        self.host = Host.objects.create(
            fqdn="test_fqdn",
            prototype=host_prototype,
            provider=provider,
            config=config,
        )
        self.cluster_conf_updated_str = "Cluster configuration updated"
        self.host_conf_updated_str = "Host configuration updated"
        self.host_updated = "Host updated"
        self.component_conf_updated_str = "Component configuration updated"
        self.service_conf_updated_str = "Service configuration updated"
        self.cluster_deleted_str = "Cluster deleted"
        self.action_display_name = "test_cluster_action"

    def check_log_no_obj(self, log: AuditLog, operation_result: AuditLogOperationResult, user: User) -> None:
        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, "Cluster created")
        self.assertEqual(log.operation_type, AuditLogOperationType.CREATE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, user.username)
        self.assertEqual(log.object_changes, {})

    def check_log(
        self,
        log: AuditLog,
        obj: Cluster | Host | HostComponent | Service | Component,
        obj_name: str,
        obj_type: AuditObjectType,
        operation_name: str,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult = AuditLogOperationResult.SUCCESS,
        user: User | None = None,
        object_changes: dict | None = None,
        object_is_deleted: bool = False,
    ) -> None:
        if object_changes is None:
            object_changes = {}
        if user is None:
            user = self.test_user

        self.assertEqual(log.audit_object.object_id, obj.pk)
        self.assertEqual(log.audit_object.object_name, obj_name)
        self.assertEqual(log.audit_object.object_type, obj_type)
        self.assertEqual(log.audit_object.is_deleted, object_is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, user.username)
        self.assertDictEqual(log.object_changes, object_changes)

    def check_log_denied(self, log: AuditLog, operation_name: str, operation_type: AuditLogOperationType) -> None:
        self.assertEqual(log.audit_object.object_id, self.cluster.pk)
        self.assertEqual(log.audit_object.object_name, self.cluster.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.CLUSTER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, operation_type)
        self.assertEqual(log.operation_result, AuditLogOperationResult.DENIED)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.no_rights_user.username)
        self.assertEqual(log.object_changes, {})

    def check_cluster_update_config(self, log: AuditLog) -> None:
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=self.cluster_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
        )

    def check_cluster_delete_failed_not_found(self, log: AuditLog):
        self.assertFalse(log.audit_object)
        self.assertEqual(log.operation_name, self.cluster_deleted_str)
        self.assertEqual(log.operation_type, AuditLogOperationType.DELETE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.FAIL)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.test_user.username)
        self.assertEqual(log.object_changes, {})

    def check_action_log(
        self,
        log: AuditLog,
        operation_name: str,
        operation_result: AuditLogOperationResult,
    ) -> None:
        self.assertEqual(log.audit_object.object_id, self.cluster.pk)
        self.assertEqual(log.audit_object.object_name, self.cluster.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.CLUSTER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.object_changes, {})

    def get_sc(self) -> Component:
        service_component_prototype = Prototype.objects.create(bundle=self.bundle, type="component")

        return Component.objects.create(
            cluster=self.cluster,
            service=self.service,
            prototype=service_component_prototype,
        )

    def get_cluster_service_for_bind(self):
        bundle = Bundle.objects.create(name="test_bundle_2")
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster", name="Export_cluster")
        service_prototype = Prototype.objects.create(
            bundle=bundle,
            type="service",
            name="Export_service",
            display_name="Export service",
        )
        PrototypeExport.objects.create(prototype=cluster_prototype, name="cluster_export")
        PrototypeExport.objects.create(prototype=service_prototype, name="service_export")

        cluster = Cluster.objects.create(prototype=cluster_prototype, name="Export cluster")
        service = Service.objects.create(prototype=service_prototype, cluster=cluster)

        PrototypeImport.objects.create(prototype=self.cluster_prototype, name="Export_cluster")
        PrototypeImport.objects.create(prototype=self.cluster_prototype, name="Export_service")
        PrototypeImport.objects.create(prototype=self.service_prototype, name="Export_cluster")
        PrototypeImport.objects.create(prototype=self.service_prototype, name="Export_service")

        return cluster, service

    def get_component(self) -> tuple[Component, ConfigLog]:
        config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = config_log.pk
        config.save(update_fields=["current"])

        prototype = Prototype.objects.create(bundle=self.bundle, type="component")

        return (
            Component.objects.create(
                cluster=self.cluster,
                service=self.service,
                prototype=prototype,
                config=config,
            ),
            config_log,
        )

    def add_no_rights_user_cluster_view_rights(self) -> None:
        role = Role.objects.get(name="View cluster configurations")
        policy = Policy.objects.create(name="test_policy", role=role)
        policy.group.add(self.no_rights_user_group)
        policy.add_object(self.cluster)
        policy.apply()

    def test_create(self):
        cluster = self.create_cluster(bundle_pk=self.bundle.pk, name=self.test_cluster_name)

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj_name=self.test_cluster_name,
            obj=cluster,
            obj_type=AuditObjectType.CLUSTER,
            operation_name="Cluster created",
            operation_type=AuditLogOperationType.CREATE,
        )

        with self.assertRaises(AssertionError):
            self.create_cluster(bundle_pk=self.bundle.pk, name=self.test_cluster_name)

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_no_obj(
            log=log,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.test_user,
        )

    def test_create_denied(self):
        with self.no_rights_user_logged_in, self.assertRaises(AssertionError):
            self.create_cluster(bundle_pk=self.bundle.pk, name=self.test_cluster_name)

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_no_obj(
            log=log,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_delete_two_clusters(self):
        cluster_bundle_filename = "test_cluster_bundle.tar"
        provider_bundle_filename = "test_provider_bundle.tar"

        with open(
            Path(self.base_dir, "python/audit/tests/files", cluster_bundle_filename),
            encoding=settings.ENCODING_UTF_8,
        ) as f:
            self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        cluster_bundle_response: Response = self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": cluster_bundle_filename},
        )

        with open(
            Path(self.base_dir, "python/audit/tests/files", provider_bundle_filename),
            encoding=settings.ENCODING_UTF_8,
        ) as f:
            self.client.post(
                path=reverse(viewname="v1:upload-bundle"),
                data={"file": f},
            )

        provider_bundle_response: Response = self.client.post(
            path=reverse(viewname="v1:load-bundle"),
            data={"bundle_file": provider_bundle_filename},
        )

        cluster_1 = self.create_cluster(bundle_pk=cluster_bundle_response.data["id"], name="new-test-cluster-1")
        self.create_cluster(bundle_pk=cluster_bundle_response.data["id"], name="new_test_cluster_2")

        provider_prototype = Prototype.objects.create(bundle_id=provider_bundle_response.data["id"], type="provider")
        provider_response: Response = self.client.post(
            path=reverse(viewname="v1:provider"),
            data={
                "name": "new_test_provider",
                "prototype_id": provider_prototype.pk,
            },
        )

        host_prototype = Prototype.objects.create(bundle_id=provider_bundle_response.data["id"], type="host")
        host_1_response: Response = self.client.post(
            path=reverse(viewname="v1:host"),
            data={
                "prototype_id": host_prototype.pk,
                "provider_id": provider_response.data["id"],
                "fqdn": "test-fqdn-1",
            },
        )
        self.client.post(
            path=reverse(viewname="v1:host"),
            data={
                "prototype_id": host_prototype.pk,
                "provider_id": provider_response.data["id"],
                "fqdn": "test-fqdn-2",
            },
        )

        self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": cluster_1.pk}),
            data={"host_id": host_1_response.data["id"]},
            content_type=APPLICATION_JSON,
        )

        service_prototype = Prototype.objects.create(
            bundle=self.bundle,
            type="service",
            display_name="new_test_service",
        )
        service = Service.objects.create(
            prototype=service_prototype,
            cluster_id=cluster_1.pk,
        )
        self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster_1.pk}),
            data={
                "service_id": service.pk,
                "prototype_id": service_prototype.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertFalse(AuditObject.objects.filter(is_deleted=True))

        self.client.delete(path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_1.pk}))

        self.assertEqual(AuditObject.objects.filter(is_deleted=True).count(), 1)

    def test_delete(self):
        self.client.delete(path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=self.cluster_deleted_str,
            operation_type=AuditLogOperationType.DELETE,
        )

        response: Response = self.client.delete(
            path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_cluster_delete_failed_not_found(log=log)

    def test_delete_failed(self):
        cluster_pks = Service.objects.all().values_list("pk", flat=True).order_by("-pk")
        res = self.client.delete(path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_pks[0] + 1}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_404_NOT_FOUND)
        self.check_cluster_delete_failed_not_found(log=log)

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log_denied(
            log=log,
            operation_name=self.cluster_deleted_str,
            operation_type=AuditLogOperationType.DELETE,
        )

    def test_delete_no_rights_denied(self):
        self.add_no_rights_user_cluster_view_rights()
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_denied(
            log=log,
            operation_name=self.cluster_deleted_str,
            operation_type=AuditLogOperationType.DELETE,
        )

    def test_update(self):
        self.client.patch(
            path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "display_name": "test_cluster_another_display_name",
                "name": self.test_cluster_name,
                "description": self.description,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.test_cluster_name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name="Cluster updated",
            operation_type=AuditLogOperationType.UPDATE,
            object_changes={
                "current": {
                    "description": self.description,
                    "name": self.test_cluster_name,
                },
                "previous": {
                    "description": "",
                    "name": "test_cluster_2",
                },
            },
        )

    def test_update_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
                data={"display_name": "test_cluster_another_display_name"},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log_denied(
            log=log,
            operation_name="Cluster updated",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_bind_unbind_empty_data(self):
        self.client.post(
            path=reverse(viewname="v1:cluster-bind", kwargs={"cluster_id": self.cluster.pk}),
            data={},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name="Cluster bound to",
            operation_result=AuditLogOperationResult.FAIL,
            operation_type=AuditLogOperationType.UPDATE,
        )

        self.client.delete(
            path=reverse(viewname="v1:cluster-bind-details", kwargs={"cluster_id": self.cluster.pk, "bind_id": 411}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name="unbound",
            operation_result=AuditLogOperationResult.FAIL,
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_bind_unbind_cluster_to_cluster(self):
        cluster, _ = self.get_cluster_service_for_bind()
        self.client.post(
            path=reverse(viewname="v1:cluster-bind", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "export_cluster_id": cluster.pk,
                "export_service_id": None,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"Cluster bound to {cluster.name}",
            operation_type=AuditLogOperationType.UPDATE,
        )

        bind = ClusterBind.objects.first()
        self.client.delete(
            path=reverse(
                viewname="v1:cluster-bind-details", kwargs={"cluster_id": self.cluster.pk, "bind_id": bind.pk}
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{cluster.name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_bind_unbind_service_to_cluster(self):
        cluster, service = self.get_cluster_service_for_bind()
        self.client.post(
            path=reverse(viewname="v1:cluster-bind", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "export_cluster_id": cluster.pk,
                "export_service_id": service.pk,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"Cluster bound to {cluster.name}/{service.display_name}",
            operation_type=AuditLogOperationType.UPDATE,
        )

        bind = ClusterBind.objects.first()
        self.client.delete(
            path=reverse(
                viewname="v1:cluster-bind-details", kwargs={"cluster_id": self.cluster.pk, "bind_id": bind.pk}
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{cluster.name}/{service.display_name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_bind_unbind_service_to_cluster_denied(self):
        cluster, service = self.get_cluster_service_for_bind()
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:cluster-bind", kwargs={"cluster_id": self.cluster.pk}),
                data={
                    "export_cluster_id": cluster.pk,
                    "export_service_id": service.pk,
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log_denied(
            log=log,
            operation_name=f"Cluster bound to {cluster.name}/{service.display_name}",
            operation_type=AuditLogOperationType.UPDATE,
        )

        self.client.post(
            path=reverse(viewname="v1:cluster-bind", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "export_cluster_id": cluster.pk,
                "export_service_id": service.pk,
            },
            content_type=APPLICATION_JSON,
        )

        bind = ClusterBind.objects.first()
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(
                    viewname="v1:cluster-bind-details",
                    kwargs={"cluster_id": self.cluster.pk, "bind_id": bind.pk},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log_denied(
            log=log,
            operation_name=f"{cluster.name}/{service.display_name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_update_config(self):
        self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"cluster_id": self.cluster.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_cluster_update_config(log)

    def test_update_config_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:config-history", kwargs={"cluster_id": self.cluster.pk}),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log_denied(
            log=log,
            operation_name=self.cluster_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_add_host_success_and_fail(self):
        self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": self.cluster.pk}),
            data={"host_id": self.host.pk},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"[{self.host.fqdn}] host(s) added",
            operation_type=AuditLogOperationType.UPDATE,
        )

        self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": self.cluster.pk}),
            data={"host_id": 10000},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name="[] host(s) added",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.FAIL,
        )

    def test_add_host_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:host", kwargs={"cluster_id": self.cluster.pk}),
                data={"host_id": self.host.pk},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log_denied(
            log=log,
            operation_name=f"[{self.host.fqdn}] host(s) added",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_remove_host_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v1:host-details", kwargs={"cluster_id": self.cluster.pk, "host_id": 10000}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(log.audit_object.object_id, self.cluster.pk)
        self.assertEqual(log.audit_object.object_name, self.cluster.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.CLUSTER)
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.FAIL)
        self.assertEqual(log.operation_name, "host removed")

    def test_update_host_config(self):
        self.client.post(
            path=reverse(
                viewname="v1:config-history",
                kwargs={"cluster_id": self.cluster.pk, "host_id": self.host.pk},
            ),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.host,
            obj_name=self.host.name,
            obj_type=AuditObjectType.HOST,
            operation_name=self.host_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_update_host(self):
        data = {"description": self.description}
        self.cluster.prototype.allow_maintenance_mode = True
        self.cluster.prototype.save(update_fields=["allow_maintenance_mode"])
        self.host.cluster = self.cluster
        self.host.save(update_fields=["cluster"])
        self.client.patch(
            path=reverse(
                viewname="v1:host-details",
                kwargs={"cluster_id": self.cluster.pk, "host_id": self.host.pk},
            ),
            data=data,
            content_type=APPLICATION_JSON,
        )
        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.check_log(
            log=log,
            obj=self.host,
            obj_name=self.host.name,
            obj_type=AuditObjectType.HOST,
            operation_name=self.host_updated,
            operation_type=AuditLogOperationType.UPDATE,
            object_changes={
                "current": data,
                "previous": {"description": ""},
            },
        )
        self.client.patch(
            path=reverse(
                viewname="v1:host-details",
                kwargs={"cluster_id": self.cluster.pk, "host_id": self.host.pk},
            ),
            data={"fqdn": "new-test-fqdn"},
            content_type=APPLICATION_JSON,
        )
        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        self.check_log(
            log=log,
            obj=self.host,
            obj_name=self.host.name,
            obj_type=AuditObjectType.HOST,
            operation_name=self.host_updated,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.FAIL,
        )

    def test_update_host_config_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:config-history",
                    kwargs={"cluster_id": self.cluster.pk, "host_id": self.host.pk},
                ),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.host,
            obj_name=self.host.name,
            obj_type=AuditObjectType.HOST,
            operation_name=self.host_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_hostcomponent(self):
        self.host.cluster = self.cluster
        self.host.save(update_fields=["cluster"])

        self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "hc": [
                    {
                        "component_id": self.get_sc().pk,
                        "host_id": self.host.pk,
                        "service_id": self.service.pk,
                    },
                ],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name="Host-Component map updated",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_update_hostcomponent_denied(self):
        self.host.cluster = self.cluster
        self.host.save(update_fields=["cluster"])

        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:host-component", kwargs={"cluster_id": self.cluster.pk}),
                data={
                    "hc": [
                        {
                            "component_id": self.get_sc().pk,
                            "host_id": self.host.pk,
                            "service_id": self.service.pk,
                        },
                    ],
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log_denied(
            log=log,
            operation_name="Host-Component map updated",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_import(self):
        self.client.post(
            path=reverse(viewname="v1:cluster-import", kwargs={"cluster_id": self.cluster.pk}),
            data={"bind": []},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name="Cluster import updated",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_import_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:cluster-import", kwargs={"cluster_id": self.cluster.pk}),
                data={"bind": []},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log_denied(
            log=log,
            operation_name="Cluster import updated",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_add_service(self):
        cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_3")
        self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster.pk}),
            data={
                "service_id": self.service.pk,
                "prototype_id": self.service_prototype.pk,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=cluster,
            obj_name=cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.service.display_name} service added",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_add_service_via_data(self):
        cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_3")
        self.client.post(
            path=reverse(viewname="v1:service"),
            data={
                "cluster_id": cluster.pk,
                "service_id": self.service.pk,
                "prototype_id": self.service_prototype.pk,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=cluster,
            obj_name=cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.service.display_name} service added",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_add_service_denied(self):
        cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_3")
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster.pk}),
                data={
                    "service_id": self.service.pk,
                    "prototype_id": self.service_prototype.pk,
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=cluster,
            obj_name=cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.service.display_name} service added",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_add_service_failed(self):
        cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_3")
        response: Response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster.pk}),
            data={"prototype_id": "some-string"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_log(
            log=log,
            obj=cluster,
            obj_name=cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name="service added",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.FAIL,
        )

    def test_delete_service(self):
        self.client.delete(
            path=reverse(
                viewname="v1:service-details",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=f"{self.service.display_name} service removed",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_delete_service_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                path=reverse(
                    viewname="v1:service-details",
                    kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log_denied(
            log=log,
            operation_name=f"{self.service.display_name} service removed",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_bind_unbind_cluster_to_service(self):
        cluster, _ = self.get_cluster_service_for_bind()
        self.client.post(
            path=reverse(
                viewname="v1:service-bind",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
            ),
            data={"export_cluster_id": cluster.pk},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=f"Service bound to {cluster.name}",
            operation_type=AuditLogOperationType.UPDATE,
        )

        bind = ClusterBind.objects.first()
        self.client.delete(
            path=reverse(
                viewname="v1:service-bind-details",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.service.pk,
                    "bind_id": bind.pk,
                },
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=f"{cluster.name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_bind_unbind_service_to_service(self):
        cluster, service = self.get_cluster_service_for_bind()
        self.client.post(
            path=reverse(
                viewname="v1:service-bind",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
            ),
            data={"export_cluster_id": cluster.pk, "export_service_id": service.pk},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=f"Service bound to {cluster.name}/{service.display_name}",
            operation_type=AuditLogOperationType.UPDATE,
        )

        bind = ClusterBind.objects.first()
        self.client.delete(
            path=reverse(
                viewname="v1:service-bind-details",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.service.pk,
                    "bind_id": bind.pk,
                },
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=f"{cluster.name}/{service.display_name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_bind_unbind_cluster_to_service_denied(self):
        cluster, _ = self.get_cluster_service_for_bind()
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:service-bind",
                    kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
                ),
                data={"export_cluster_id": cluster.pk},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=f"Service bound to {cluster.name}",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

        self.client.post(
            path=reverse(
                viewname="v1:service-bind",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
            ),
            data={"export_cluster_id": cluster.pk},
            content_type=APPLICATION_JSON,
        )
        bind = ClusterBind.objects.first()

        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                reverse(
                    viewname="v1:service-bind-details",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service.pk,
                        "bind_id": bind.pk,
                    },
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=f"{cluster.name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_bind_unbind_service_to_service_denied(self):
        cluster, service = self.get_cluster_service_for_bind()
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:service-bind",
                    kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
                ),
                data={"export_cluster_id": cluster.pk, "export_service_id": service.pk},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=f"Service bound to {cluster.name}/{service.display_name}",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

        self.client.post(
            path=reverse(
                viewname="v1:service-bind",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
            ),
            data={"export_cluster_id": cluster.pk, "export_service_id": service.pk},
            content_type=APPLICATION_JSON,
        )
        bind = ClusterBind.objects.first()

        with self.no_rights_user_logged_in:
            response: Response = self.client.delete(
                reverse(
                    viewname="v1:service-bind-details",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service.pk,
                        "bind_id": bind.pk,
                    },
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=f"{cluster.name}/{service.display_name} unbound",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_component_config(self):
        component, _ = self.get_component()
        self.client.post(
            path=reverse(
                viewname="v1:config-history",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.service.pk,
                    "component_id": component.pk,
                },
            ),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=component,
            obj_name=f"{self.cluster.name}/{self.service.display_name}/{component.display_name}",
            obj_type=AuditObjectType.COMPONENT,
            operation_name=self.component_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_update_component_config_denied(self):
        component, _ = self.get_component()
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:config-history",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service.pk,
                        "component_id": component.pk,
                    },
                ),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=component,
            obj_name=f"{self.cluster.name}/{self.service.display_name}/{component.display_name}",
            obj_type=AuditObjectType.COMPONENT,
            operation_name=self.component_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_update_service_config(self):
        config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = config_log.pk
        config.save(update_fields=["current"])

        self.service.config = config
        self.service.save(update_fields=["config"])
        self.client.post(
            path=reverse(
                viewname="v1:config-history",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.service.pk,
                },
            ),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_update_service_config_denied(self):
        config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = config_log.pk
        config.save(update_fields=["current"])

        self.service.config = config
        self.service.save(update_fields=["config"])
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:config-history",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service.pk,
                    },
                ),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_service_import(self):
        self.client.post(
            path=reverse(
                viewname="v1:service-import",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
            ),
            data={"bind": []},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name="Service import updated",
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_service_import_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:service-import",
                    kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
                ),
                data={"bind": []},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name="Service import updated",
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_cluster_config_restore(self):
        self.client.patch(
            path=reverse(
                viewname="v1:config-history-version-restore",
                kwargs={"cluster_id": self.cluster.pk, "version": self.config_log.pk},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_cluster_update_config(log)

    def test_cluster_config_restore_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    viewname="v1:config-history-version-restore",
                    kwargs={"cluster_id": self.cluster.pk, "version": self.config_log.pk},
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.cluster,
            obj_name=self.cluster.name,
            obj_type=AuditObjectType.CLUSTER,
            operation_name=self.cluster_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_host_config_restore(self):
        self.client.patch(
            path=reverse(
                viewname="v1:config-history-version-restore",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "host_id": self.host.pk,
                    "version": self.config_log.pk,
                },
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.host,
            obj_name=self.host.fqdn,
            obj_type=AuditObjectType.HOST,
            operation_name=self.host_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_host_config_restore_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    viewname="v1:config-history-version-restore",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "host_id": self.host.pk,
                        "version": self.config_log.pk,
                    },
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.host,
            obj_name=self.host.fqdn,
            obj_type=AuditObjectType.HOST,
            operation_name=self.host_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_component_config_restore(self):
        component, config_log = self.get_component()
        self.client.patch(
            path=reverse(
                viewname="v1:config-history-version-restore",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.service.pk,
                    "component_id": component.pk,
                    "version": config_log.pk,
                },
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=component,
            obj_name=f"{self.cluster.name}/{self.service.display_name}/{component.display_name}",
            obj_type=AuditObjectType.COMPONENT,
            operation_name=self.component_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_component_config_restore_denied(self):
        component, config_log = self.get_component()
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    viewname="v1:config-history-version-restore",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service.pk,
                        "component_id": component.pk,
                        "version": config_log.pk,
                    },
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=component,
            obj_name=f"{self.cluster.name}/{self.service.display_name}/{component.display_name}",
            obj_type=AuditObjectType.COMPONENT,
            operation_name=self.component_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_service_config_restore(self):
        config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = config_log.pk
        config.save(update_fields=["current"])

        self.service.config = config
        self.service.save(update_fields=["config"])
        self.client.patch(
            path=reverse(
                viewname="v1:config-history-version-restore",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.service.pk,
                    "version": config_log.pk,
                },
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
        )

    def test_service_config_restore_denied(self):
        config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = config_log.pk
        config.save(update_fields=["current"])

        self.service.config = config
        self.service.save(update_fields=["config"])
        with self.no_rights_user_logged_in:
            response: Response = self.client.patch(
                path=reverse(
                    viewname="v1:config-history-version-restore",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service.pk,
                        "version": config_log.pk,
                    },
                ),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            obj=self.service,
            obj_name=f"{self.cluster.name}/{self.service.display_name}",
            obj_type=AuditObjectType.SERVICE,
            operation_name=self.service_conf_updated_str,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_action_launch(self):
        action = Action.objects.create(
            display_name=self.action_display_name,
            prototype=self.cluster_prototype,
            type="job",
            state_available="any",
        )
        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse(viewname="v1:run-task", kwargs={"cluster_id": self.cluster.pk, "action_id": action.pk})
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(
            log=log,
            operation_name=f"{self.action_display_name} action launched",
            operation_result=AuditLogOperationResult.SUCCESS,
        )

    def test_do_upgrade(self):
        action = Action.objects.create(
            display_name=self.action_display_name,
            prototype=self.cluster_prototype,
            type="job",
            state_available="any",
        )
        upgrade = Upgrade.objects.create(
            name="test_upgrade",
            bundle=self.bundle,
            action=action,
            min_version="1",
            max_version="99",
        )

        with (
            patch("api.cluster.views.do_upgrade", return_value={}),
            patch("api.cluster.views.check_obj"),
        ):
            self.client.post(
                path=reverse(
                    viewname="v1:do-cluster-upgrade",
                    kwargs={"cluster_id": self.cluster.pk, "upgrade_id": upgrade.pk},
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(
            log=log,
            operation_name=f"{self.action_display_name} upgrade launched",
            operation_result=AuditLogOperationResult.SUCCESS,
        )

    def test_do_upgrade_no_action(self):
        upgrade = Upgrade.objects.create(
            name="test_upgrade",
            bundle=self.bundle,
            min_version="1",
            max_version="99",
        )

        with (
            patch("api.cluster.views.do_upgrade", return_value={}),
            patch("api.cluster.views.check_obj"),
        ):
            self.client.post(
                path=reverse(
                    viewname="v1:do-cluster-upgrade",
                    kwargs={"cluster_id": self.cluster.pk, "upgrade_id": upgrade.pk},
                ),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(
            log=log,
            operation_name=f"Upgraded to {upgrade.name}",
            operation_result=AuditLogOperationResult.SUCCESS,
        )

    def test_do_upgrade_no_upgrade(self):
        self.client.post(
            path=reverse(
                viewname="v1:do-cluster-upgrade",
                kwargs={"cluster_id": self.cluster.pk, "upgrade_id": 1},
            ),
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_action_log(
            log=log,
            operation_name="Upgraded to",
            operation_result=AuditLogOperationResult.FAIL,
        )
