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
    Host,
    HostComponent,
    HostProvider,
    ObjectConfig,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    ServiceComponent,
)
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestCluster(BaseTestCase):
    # pylint: disable=too-many-instance-attributes

    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.test_cluster_name = "test_cluster"
        self.cluster_prototype = Prototype.objects.create(bundle=self.bundle, type="cluster")
        PrototypeImport.objects.create(prototype=self.cluster_prototype)
        config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.cluster = Cluster.objects.create(
            prototype=self.cluster_prototype, name="test_cluster_2", config=config
        )
        self.service_prototype = Prototype.objects.create(
            bundle=self.bundle,
            type="service",
            display_name="test_service",
        )
        PrototypeExport.objects.create(prototype=self.service_prototype)
        self.service = ClusterObject.objects.create(
            prototype=self.service_prototype,
            cluster=self.cluster,
        )

        provider_prototype = Prototype.objects.create(bundle=self.bundle, type="provider")
        provider = HostProvider.objects.create(
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

    def create_cluster(self):
        return self.client.post(
            path=reverse("cluster"),
            data={
                "bundle_id": self.bundle.pk,
                "display_name": f"{self.test_cluster_name}_display",
                "name": self.test_cluster_name,
                "prototype_id": self.cluster_prototype.pk,
            },
        )

    def test_create(self):
        res: Response = self.create_cluster()

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.test_cluster_name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Cluster created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        self.create_cluster()

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == "Cluster created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Fail
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update(self):
        self.client.patch(
            path=reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"display_name": "test_cluster_another_display_name"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Cluster updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_bind_unbind(self):
        self.client.post(
            path=reverse("cluster-bind", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "export_cluster_id": self.cluster.pk,
                "export_service_id": self.service.pk,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == (
            f"Cluster bound to {self.cluster.name}/{self.service.display_name}"
        )
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        bind = ClusterBind.objects.first()
        self.client.delete(
            path=reverse(
                "cluster-bind-details", kwargs={"cluster_id": self.cluster.pk, "bind_id": bind.pk}
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == f"{self.cluster.name}/{self.service.display_name} unbound"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_config(self):
        self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Cluster configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_add_host(self):
        self.client.post(
            path=reverse("host", kwargs={"cluster_id": self.cluster.pk}),
            data={"host_id": self.host.pk},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == f"{self.host.fqdn} added"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_host_config(self):
        self.client.post(
            path=reverse(
                "config-history",
                kwargs={"cluster_id": self.cluster.pk, "host_id": self.host.pk},
            ),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.host.pk
        assert log.audit_object.object_name == self.host.fqdn
        assert log.audit_object.object_type == AuditObjectType.Host
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Host configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_hostcomponent(self):
        service_component_prototype = Prototype.objects.create(bundle=self.bundle, type="component")
        service_component = ServiceComponent.objects.create(
            cluster=self.cluster,
            service=self.service,
            prototype=service_component_prototype,
        )
        hc = HostComponent.objects.create(
            cluster=self.cluster,
            host=self.host,
            service=self.service,
            component=service_component,
        )
        self.host.cluster = self.cluster
        self.host.save(update_fields=["cluster"])

        self.client.post(
            path=reverse("host-component", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "hc": [
                    {
                        "component_id": hc.pk,
                        "host_id": self.host.pk,
                        "service_id": self.service.pk,
                    }
                ]
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Host-Component map updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_import(self):
        self.client.post(
            path=reverse("cluster-import", kwargs={"cluster_id": self.cluster.pk}),
            data={"bind": []},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Cluster import updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_add_service(self):
        cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_3")
        self.client.post(
            path=reverse("service", kwargs={"cluster_id": cluster.pk}),
            data={
                "service_id": self.service.pk,
                "prototype_id": self.service_prototype.pk,
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == cluster.pk
        assert log.audit_object.object_name == cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == "test_service service added"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_delete_service(self):
        self.client.delete(
            path=reverse(
                "service-details",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == f"{self.service.display_name} service removed"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_bind_unbind_service(self):
        bundle = Bundle.objects.create(name="test_bundle_2")
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        cluster = Cluster.objects.create(prototype=cluster_prototype, name="test_cluster_3")
        PrototypeExport.objects.create(prototype=cluster_prototype)
        PrototypeImport.objects.create(prototype=self.service_prototype)

        self.client.post(
            path=reverse(
                "service-bind",
                kwargs={"cluster_id": cluster.pk, "service_id": self.service.pk},
            ),
            data={"export_cluster_id": cluster.pk},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.service.pk
        assert log.audit_object.object_name == self.service.name
        assert log.audit_object.object_type == AuditObjectType.Service
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Service bound to test_cluster_3/test_service"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        bind = ClusterBind.objects.first()
        self.client.delete(
            reverse(
                "service-bind-details",
                kwargs={
                    "cluster_id": cluster.pk,
                    "service_id": self.service.pk,
                    "bind_id": bind.pk,
                },
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.service.pk
        assert log.audit_object.object_name == self.service.name
        assert log.audit_object.object_type == AuditObjectType.Service
        assert not log.audit_object.is_deleted
        assert log.operation_name == 'test_cluster_3/test_service unbound'
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_component_config(self):
        config = ObjectConfig.objects.create(current=2, previous=2)
        ConfigLog.objects.create(obj_ref=config, config="{}")
        prototype = Prototype.objects.create(bundle=self.bundle, type="component")
        component = ServiceComponent.objects.create(
            cluster=self.cluster,
            service=self.service,
            prototype=prototype,
            config=config,
        )
        self.client.post(
            path=reverse(
                "config-history",
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

        assert log.audit_object.object_id == component.pk
        assert log.audit_object.object_name == component.name
        assert log.audit_object.object_type == AuditObjectType.Component
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Component configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_service_config(self):
        config = ObjectConfig.objects.create(current=2, previous=2)
        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.service.config = config
        self.service.save(update_fields=["config"])
        self.client.post(
            path=reverse(
                "config-history",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.service.pk,
                },
            ),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.service.pk
        assert log.audit_object.object_name == self.service.name
        assert log.audit_object.object_type == AuditObjectType.Service
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Service configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_service_import(self):
        self.client.post(
            path=reverse(
                "service-import",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk},
            ),
            data={"bind": []},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.service.pk
        assert log.audit_object.object_name == self.service.name
        assert log.audit_object.object_type == AuditObjectType.Service
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Service import updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
