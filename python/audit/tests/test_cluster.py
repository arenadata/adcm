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
from cm.models import Bundle, Prototype
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestCluster(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.test_cluster_name = "test_cluster"
        self.prototype = Prototype.objects.create(bundle=self.bundle, type="cluster")

    def create_cluster(self):
        return self.client.post(
            path=reverse("cluster"),
            data={
                "bundle_id": self.bundle.pk,
                "display_name": f"{self.test_cluster_name}_display",
                "name": self.test_cluster_name,
                "prototype_id": self.prototype.pk,
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
