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
    ObjectConfig,
    Prototype,
    ServiceComponent,
)

from adcm.tests.base import BaseTestCase


class TestComponent(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        cluster = Cluster.objects.create(prototype=cluster_prototype, name="test_cluster")
        service_prototype = Prototype.objects.create(bundle=bundle, type="service")
        self.service = ClusterObject.objects.create(prototype=service_prototype, cluster=cluster)
        component_prototype = Prototype.objects.create(bundle=bundle, type="component")
        config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.component = ServiceComponent.objects.create(
            prototype=component_prototype,
            cluster=cluster,
            service=self.service,
            config=config,
        )

    def check_component_update(self, log: AuditLog):
        assert log.audit_object.object_id == self.component.pk
        assert log.audit_object.object_name == self.component.name
        assert log.audit_object.object_type == AuditObjectType.Component
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Component configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update(self):
        self.client.patch(
            path=f"/api/v1/component/{self.component.pk}/config/history/1/restore/",
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_component_update(log)

    def test_update_via_service(self):
        self.client.post(
            path=f"/api/v1/service/{self.service.pk}/component/"
            f"{self.component.pk}/config/history/",
            data={"config": {}},
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_component_update(log)
