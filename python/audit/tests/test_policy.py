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
from cm.models import Bundle, Cluster, Prototype
from django.urls import reverse
from rbac.models import Policy, Role, RoleTypes, User
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestPolicy(BaseTestCase):
    # pylint: disable=too-many-instance-attributes

    def setUp(self) -> None:
        super().setUp()

        self.name = "test_policy"
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster_name = "test_cluster"
        self.cluster = Cluster.objects.create(name=self.cluster_name, prototype=prototype)
        self.role = Role.objects.create(
            name="test_role",
            display_name="test_role",
            type=RoleTypes.role,
            parametrized_by_type=["cluster"],
            module_name="rbac.roles",
            class_name="ObjectRole",
        )
        self.policy = Policy.objects.create(name="test_policy_2", built_in=False)
        self.list_name = "rbac:policy-list"
        self.detail_name = "rbac:policy-detail"
        self.policy_updated_str = "Policy updated"

    def check_log(
        self,
        log: AuditLog,
        operation_name: str,
        operation_type: AuditLogOperationType,
        operation_result: AuditLogOperationResult,
        user: User,
    ) -> None:
        assert log.audit_object.object_id == self.policy.pk
        assert log.audit_object.object_name == self.policy.name
        assert log.audit_object.object_type == AuditObjectType.Policy
        assert not log.audit_object.is_deleted
        assert log.operation_name == operation_name
        assert log.operation_type == operation_type
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(
            path=reverse(self.list_name),
            data={
                "name": self.name,
                "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.name
        assert log.audit_object.object_type == AuditObjectType.Policy
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Policy created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse(self.list_name),
                data={
                    "name": self.name,
                    "object": [
                        {"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}
                    ],
                    "role": {"id": self.role.pk},
                    "user": [{"id": self.test_user.pk}],
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        assert not log.audit_object
        assert log.operation_name == "Policy created"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Denied
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.no_rights_user.pk
        assert isinstance(log.object_changes, dict)

    def test_delete(self):
        self.client.delete(
            path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Policy deleted",
            operation_type=AuditLogOperationType.Delete,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log(
            log=log,
            operation_name="Policy deleted",
            operation_type=AuditLogOperationType.Delete,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_update_put(self):
        self.client.put(
            path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
            data={
                "name": self.policy.name,
                "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
                "description": "new_test_description",
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name=self.policy_updated_str,
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_update_put_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.put(
                path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
                data={
                    "name": self.policy.name,
                    "object": [
                        {"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}
                    ],
                    "role": {"id": self.role.pk},
                    "user": [{"id": self.test_user.pk}],
                    "description": "new_test_description",
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log(
            log=log,
            operation_name=self.policy_updated_str,
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_update_patch(self):
        self.client.patch(
            path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
            data={
                "object": [{"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
                "description": "new_test_description",
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name=self.policy_updated_str,
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_update_patch_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.patch(
                path=reverse(self.detail_name, kwargs={"pk": self.policy.pk}),
                data={
                    "object": [
                        {"id": self.cluster.pk, "name": self.cluster_name, "type": "cluster"}
                    ],
                    "role": {"id": self.role.pk},
                    "user": [{"id": self.test_user.pk}],
                    "description": "new_test_description",
                },
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log(
            log=log,
            operation_name=self.policy_updated_str,
            operation_type=AuditLogOperationType.Update,
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )
