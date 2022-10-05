from django.urls import reverse

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from audit.models import AuditLog
from cm.models import (
    Bundle,
    Cluster,
    ConfigLog,
    Host,
    HostProvider,
    MaintenanceModeType,
    ObjectConfig,
    Prototype,
)
from rbac.models import Group, Policy, Role, RoleTypes


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
            maintenance_mode=MaintenanceModeType.On,
            config=config,
        )

        self.group = Group.objects.create(name="test_group")
        self.role = Role.objects.create(
            name="test_role",
            display_name="test_role",
            type=RoleTypes.role,
            parametrized_by_type=["cluster"],
            module_name="rbac.roles",
            class_name="ObjectRole",
        )
        self.policy = Policy.objects.create(name="test_policy", built_in=False)

    def test_cluster_rename(self):
        new_test_cluster_name = "new-test-cluster-name"
        self.client.patch(
            path=reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"description": "test_cluster_description"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_cluster = log.audit_object

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)

        self.client.post(
            path=reverse("config-history", kwargs={"host_id": self.host.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_host = log.audit_object

        self.assertEqual(audit_object_host.object_name, self.host.fqdn)

        self.client.patch(
            path=reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk}),
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
            path=reverse("config-history", kwargs={"host_id": self.host.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_host = log.audit_object

        self.assertEqual(audit_object_host.object_name, self.host.fqdn)

        self.client.patch(
            path=reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"description": "test_cluster_description"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_cluster = log.audit_object

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)

        self.client.patch(
            path=reverse("host-details", kwargs={"host_id": self.host.pk}),
            data={"fqdn": new_test_host_fqdn, "maintenance_mode": MaintenanceModeType.On},
            content_type=APPLICATION_JSON,
        )

        audit_object_cluster.refresh_from_db()
        audit_object_host.refresh_from_db()

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)
        self.assertEqual(audit_object_host.object_name, new_test_host_fqdn)

    def test_group_rename(self):
        new_test_group_name = "new_test_group_name"
        self.client.patch(
            path=reverse("rbac:group-detail", kwargs={"pk": self.group.pk}),
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
            path=reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"description": "test_cluster_description"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_cluster = log.audit_object

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)

        self.client.patch(
            path=reverse("rbac:group-detail", kwargs={"pk": self.group.pk}),
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
            path=reverse("rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data={
                "object": [
                    {
                        "id": self.cluster.pk,
                        "name": self.cluster.name,
                        "type": "cluster",
                    }
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
            path=reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"description": "test_cluster_description"},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()
        audit_object_cluster = log.audit_object

        self.assertEqual(audit_object_cluster.object_name, self.cluster.name)

        self.client.patch(
            path=reverse("rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data={
                "object": [
                    {
                        "id": self.cluster.pk,
                        "name": self.cluster.name,
                        "type": "cluster",
                    }
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
