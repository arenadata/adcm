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
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestGroupConfig(BaseTestCase):
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

    def check_group_config_updated(self, log: AuditLog) -> None:
        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == "test_group_config_2 configuration group updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create_for_cluster(self):
        self.create_group_config(
            name=self.name,
            object_id=self.cluster.pk,
            object_type=AuditObjectType.Cluster,
            config_id=self.config.pk,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == self.created_operation_name
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create_for_service(self):
        prototype = Prototype.objects.create(bundle=self.bundle, type="service")
        service = ClusterObject.objects.create(
            prototype=prototype, cluster=self.cluster, config=self.config
        )
        self.create_group_config(
            name=self.name,
            object_id=service.pk,
            object_type=AuditObjectType.Service,
            config_id=self.config.pk,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == service.pk
        assert log.audit_object.object_name == service.name
        assert log.audit_object.object_type == AuditObjectType.Service
        assert not log.audit_object.is_deleted
        assert log.operation_name == self.created_operation_name
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create_for_component(self):
        service_prototype = Prototype.objects.create(bundle=self.bundle, type="service")
        service = ClusterObject.objects.create(
            prototype=service_prototype, cluster=self.cluster, config=self.config
        )
        component_prototype = Prototype.objects.create(bundle=self.bundle, type="component")
        component = ServiceComponent.objects.create(
            prototype=component_prototype,
            cluster=self.cluster,
            service=service,
            config=self.config,
        )
        self.create_group_config(
            name=self.name,
            object_id=component.pk,
            object_type=AuditObjectType.Component,
            config_id=self.config.pk,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == component.pk
        assert log.audit_object.object_name == component.name
        assert log.audit_object.object_type == AuditObjectType.Component
        assert not log.audit_object.is_deleted
        assert log.operation_name == self.created_operation_name
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_delete(self):
        self.client.delete(path=reverse("group-config-detail", kwargs={"pk": self.group_config.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == f"{self.group_config.name} configuration group deleted"
        assert log.operation_type == AuditLogOperationType.Delete
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_put(self):
        self.client.put(
            path=f"/api/v1/group-config/{self.group_config.pk}/",
            data={
                "name": self.group_config.name,
                "object_id": self.cluster.pk,
                "object_type": "cluster",
                "config_id": self.config.id,
            },
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_group_config_updated(log)

    def test_update_patch(self):
        self.client.patch(
            path=f"/api/v1/group-config/{self.group_config.pk}/",
            data={
                "name": self.group_config.name,
                "object_id": self.cluster.pk,
                "object_type": "cluster",
                "config_id": self.config.id,
            },
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_group_config_updated(log)

    def test_add_remove_host(self):
        self.client.post(
            path=f"/api/v1/group-config/{self.group_config.pk}/host/",
            data={"id": self.host.id},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == (
            f"{self.host.fqdn} host added to {self.group_config.name} configuration group"
        )
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        self.client.delete(
            path=f"/api/v1/group-config/{self.group_config.pk}/host/{self.host.id}/",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.cluster.pk
        assert log.audit_object.object_name == self.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == (
            f"{self.host.fqdn} host removed from {self.group_config.name} configuration group"
        )
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
