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

from audit.models import AuditLog
from cm.models import (
    Bundle,
    Cluster,
    ConfigLog,
    Host,
    HostProvider,
    MaintenanceMode,
    ObjectConfig,
    ObjectType,
    Prototype,
)
from django.urls import reverse
from rbac.models import Group, Policy, Role, RoleTypes

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestAuditObjectRename(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster = Cluster.objects.create(prototype=cluster_prototype, name="test-cluster")

        provider_prototype = Prototype.objects.create(bundle=bundle, type="provider")
        host_prototype = Prototype.objects.create(bundle=bundle, type="host")
        provider = HostProvider.objects.create(
            name="test_provider",
            prototype=provider_prototype,
        )
        config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(obj_ref=config, config="{}")
        config.current = config_log.pk
        config.save(update_fields=["current"])

        self.host = Host.objects.create(
            fqdn="test_fqdn",
            prototype=host_prototype,
            provider=provider,
            maintenance_mode=MaintenanceMode.ON,
            config=config,
        )

        self.group = Group.objects.create(name="test_group")
        role_name = "test_role"
        self.role = Role.objects.create(
            name=role_name,
            display_name=role_name,
            type=RoleTypes.ROLE,
            parametrized_by_type=[ObjectType.CLUSTER],
            module_name="rbac.roles",
            class_name="ObjectRole",
        )
        self.policy = Policy.objects.create(name="test_policy", built_in=False)

    def test_cluster_rename(self):
        new_test_cluster_name = "new-test-cluster-name"
        self.client.patch(
            path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"description": "test_cluster_description"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_cluster = log.audit_object

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)

        self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"host_id": self.host.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_host = log.audit_object

        self.assertEqual(audit_object_host.object_name, self.host.fqdn)

        self.client.patch(
            path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"name": new_test_cluster_name},
            content_type=APPLICATION_JSON,
        )

        audit_object_cluster.refresh_from_db()
        audit_object_host.refresh_from_db()

        self.assertEqual(audit_object_cluster.object_name, new_test_cluster_name)
        self.assertEqual(audit_object_host.object_name, self.host.fqdn)

    def test_host_rename(self):
        new_test_host_fqdn = "new-test-host-fqdn"
        self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"host_id": self.host.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_host = log.audit_object

        self.assertEqual(audit_object_host.object_name, self.host.fqdn)

        self.client.patch(
            path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"description": "test_cluster_description"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_cluster = log.audit_object

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)

        self.client.patch(
            path=reverse(viewname="v1:host-details", kwargs={"host_id": self.host.pk}),
            data={"fqdn": new_test_host_fqdn, "maintenance_mode": MaintenanceMode.ON},
            content_type=APPLICATION_JSON,
        )

        audit_object_cluster.refresh_from_db()
        audit_object_host.refresh_from_db()

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)
        self.assertEqual(audit_object_host.object_name, new_test_host_fqdn)

    def test_group_rename(self):
        new_test_group_name = "new_test_group_name"
        self.client.patch(
            path=reverse(viewname="v1:rbac:group-detail", kwargs={"pk": self.group.pk}),
            data={
                "description": "test_group_description",
                "user": [{"id": self.test_user.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_group = log.audit_object

        self.assertEqual(audit_object_group.object_name, self.group.name)

        self.client.patch(
            path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"description": "test_cluster_description"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_cluster = log.audit_object

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)

        self.client.patch(
            path=reverse(viewname="v1:rbac:group-detail", kwargs={"pk": self.group.pk}),
            data={
                "name": new_test_group_name,
                "user": [{"id": self.test_user.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        audit_object_cluster.refresh_from_db()
        audit_object_group.refresh_from_db()

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)
        self.assertEqual(audit_object_group.object_name, f"{new_test_group_name} [local]")

    def test_policy_rename(self):
        new_test_policy_name = "new_test_policy_name"
        self.client.patch(
            path=reverse(viewname="v1:rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data={
                "object": [
                    {
                        "id": self.cluster.pk,
                        "name": self.cluster.name,
                        "type": "cluster",
                    },
                ],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
                "description": "test_policy_description",
            },
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_policy = log.audit_object

        self.assertEqual(audit_object_policy.object_name, self.policy.name)

        self.client.patch(
            path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"description": "test_cluster_description"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_cluster = log.audit_object

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)

        self.client.patch(
            path=reverse(viewname="v1:rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data={
                "object": [
                    {
                        "id": self.cluster.pk,
                        "name": self.cluster.name,
                        "type": "cluster",
                    },
                ],
                "role": {"id": self.role.pk},
                "user": [{"id": self.test_user.pk}],
                "name": new_test_policy_name,
            },
            content_type=APPLICATION_JSON,
        )

        audit_object_cluster.refresh_from_db()
        audit_object_policy.refresh_from_db()

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)
        self.assertEqual(audit_object_policy.object_name, new_test_policy_name)
