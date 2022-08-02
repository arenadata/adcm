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
from cm.models import Bundle, Cluster, ClusterObject, ConfigLog, ObjectConfig, Prototype

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestService(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        cluster = Cluster.objects.create(prototype=cluster_prototype, name="test_cluster")
        service_prototype = Prototype.objects.create(bundle=bundle, type="service")
        config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.service = ClusterObject.objects.create(
            prototype=service_prototype, cluster=cluster, config=config
        )

    def check_service_update(self, log: AuditLog):
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

    def test_update(self):
        self.client.post(
            path=f"/api/v1/service/{self.service.pk}/config/history/",
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_service_update(log)

    def test_restore(self):
        self.client.patch(
            path=f"/api/v1/service/{self.service.pk}/config/history/1/restore/",
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_service_update(log)

    def test_delete(self):
        self.client.delete(
            path=f"/api/v1/service/{self.service.pk}/",
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.service.cluster.pk
        assert log.audit_object.object_name == self.service.cluster.name
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == f"{self.service.display_name} service removed"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_import(self):
        self.client.post(
            path=f"/api/v1/service/{self.service.pk}/import/",
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
