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

from cm import api
from cm.models import (
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    Prototype,
    ServiceComponent,
)
from rbac.models import Group, Policy, User
from rbac.tests.test_base import RBACBaseTestCase


class PolicyTestRBAC(RBACBaseTestCase):  # pylint: disable=too-many-instance-attributes
    """Tests for applying policy with different combination of roles and object"""

    def setUp(self) -> None:
        super().setUp()

        self.user = User.objects.create(username="user", is_active=True, is_superuser=False)
        self.cluster = Cluster.objects.create(name="Cluster_1", prototype=self.clp)
        self.service_1 = ClusterObject.objects.create(cluster=self.cluster, prototype=self.sp_1)
        self.service_2 = ClusterObject.objects.create(cluster=self.cluster, prototype=self.sp_2)
        self.component_11 = ServiceComponent.objects.create(
            cluster=self.cluster,
            service=self.service_1,
            prototype=self.cop_11,
        )
        self.component_12 = ServiceComponent.objects.create(
            cluster=self.cluster,
            service=self.service_1,
            prototype=self.cop_12,
        )
        self.component_21 = ServiceComponent.objects.create(
            cluster=self.cluster,
            service=self.service_2,
            prototype=self.cop_21,
        )

    def get_hosts_and_provider(self):
        provider, _ = HostProvider.objects.get_or_create(name="provider", prototype=self.provider_prototype)
        host1 = Host.objects.create(prototype=self.host_prototype, provider=provider, fqdn="host_1")
        host2 = Host.objects.create(prototype=self.host_prototype, provider=provider, fqdn="host_2")

        return provider, host1, host2

    @staticmethod
    def clear_perm_cache(user):
        if hasattr(user, "_perm_cache"):
            delattr(user, "_perm_cache")

        if hasattr(user, "_user_perm_cache"):
            delattr(user, "_user_perm_cache")

        if hasattr(user, "_group_perm_cache"):
            delattr(user, "_group_perm_cache")

    def test_model_policy(self):
        policy = Policy.objects.create(name="MyPolicy", role=self.model_role())
        policy.user.add(self.user)

        self.assertNotIn(self.add_host_perm, self.user.user_permissions.all())
        self.assertFalse(self.user.has_perm("cm.add_host"))
        self.clear_perm_cache(self.user)

        policy.apply()

        self.assertIn(self.add_host_perm, self.user.user_permissions.all())
        self.assertTrue(self.user.has_perm("cm.add_host"))

        self.clear_perm_cache(self.user)
        policy.apply()

        self.assertTrue(self.user.has_perm("cm.add_host"))

    def test_model_policy4group(self):
        group = Group.objects.create(name="group")
        group.user_set.add(self.user)

        policy = Policy.objects.create(name="MyPolicy", role=self.model_role())
        policy.group.add(group)

        self.assertNotIn(self.add_host_perm, group.permissions.all())
        self.assertFalse(self.user.has_perm("cm.add_host"))

        self.clear_perm_cache(self.user)
        policy.apply()

        self.assertIn(self.add_host_perm, group.permissions.all())
        self.assertTrue(self.user.has_perm("cm.add_host"))

        self.clear_perm_cache(self.user)
        policy.apply()

        self.assertTrue(self.user.has_perm("cm.add_host"))

    def test_object_policy(self):
        cluster2 = Cluster.objects.create(name="Cluster_2", prototype=self.clp)
        policy = Policy.objects.create(name="MyPolicy", role=self.object_role_view_perm_cluster())
        policy.user.add(self.user)

        self.assertFalse(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.view_cluster", cluster2))

        policy.add_object(self.cluster)
        policy.apply()

        self.assertTrue(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.view_cluster", cluster2))

    def test_object_policy_remove_user(self):
        cluster2 = Cluster.objects.create(name="Cluster_2", prototype=self.clp)

        policy = Policy.objects.create(name="MyPolicy", role=self.object_role())
        policy.user.add(self.user)
        policy.add_object(self.cluster)

        self.assertFalse(self.user.has_perm("cm.view_cluster", self.cluster))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.view_cluster", cluster2))

        policy.user.remove(self.user)
        policy.apply()

        self.assertFalse(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.view_cluster", cluster2))

    def test_object_policy4group(self):
        cluster2 = Cluster.objects.create(name="Cluster_2", prototype=self.clp)
        group = Group.objects.create(name="group")
        group.user_set.add(self.user)

        policy = Policy.objects.create(name="MyPolicy", role=self.object_role())
        policy.group.add(group)

        policy.add_object(self.cluster)

        self.assertFalse(self.user.has_perm("cm.view_cluster", self.cluster))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.view_cluster", cluster2))

    def test_parent_policy4cluster(self):
        policy = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component())
        policy.user.add(self.user)
        policy.add_object(self.cluster)

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

    def test_parent_policy4service(self):
        policy = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component())
        policy.user.add(self.user)
        policy.add_object(self.service_1)

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

    def test_parent_policy4service2(self):
        policy = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component())
        policy.user.add(self.user)
        policy.add_object(self.service_2)

        self.assertFalse(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

    def test_parent_policy4component(self):
        policy = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component())
        policy.user.add(self.user)
        policy.add_object(self.component_11)

        self.assertFalse(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.view_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.view_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.view_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

    def test_parent_policy4host_in_cluster(self):
        provider, host1, host2 = self.get_hosts_and_provider()
        host3 = Host.objects.create(provider=provider, prototype=self.host_prototype, fqdn="host_3")
        api.add_host_to_cluster(self.cluster, host1)
        api.add_host_to_cluster(self.cluster, host2)
        policy = Policy.objects.create(role=self.object_role_custom_perm_cluster_host())
        policy.user.add(self.user)
        policy.add_object(self.cluster)

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host3))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host3))

    def test_parent_policy4host_in_service(self):
        _, host1, host2 = self.get_hosts_and_provider()
        api.add_host_to_cluster(self.cluster, host1)
        api.add_host_to_cluster(self.cluster, host2)
        api.add_hc(
            self.cluster,
            [
                {
                    "service_id": self.service_1.id,
                    "component_id": self.component_11.id,
                    "host_id": host1.id,
                },
                {
                    "service_id": self.service_2.id,
                    "component_id": self.component_21.id,
                    "host_id": host2.id,
                },
            ],
        )
        policy = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component_host())
        policy.user.add(self.user)
        policy.add_object(self.service_1)

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host2))

        policy.apply()

        self.assertFalse(self.user.has_perm("cm.change_confing_of_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host2))

    def test_parent_policy4host_in_component(self):
        provider, host1, host2 = self.get_hosts_and_provider()
        host3 = Host.objects.create(provider=provider, prototype=self.host_prototype, fqdn="host_3")
        api.add_host_to_cluster(self.cluster, host1)
        api.add_host_to_cluster(self.cluster, host2)
        api.add_host_to_cluster(self.cluster, host3)
        api.add_hc(
            self.cluster,
            [
                {
                    "service_id": self.service_2.id,
                    "component_id": self.component_21.id,
                    "host_id": host1.id,
                },
                {
                    "service_id": self.service_2.id,
                    "component_id": self.component_21.id,
                    "host_id": host2.id,
                },
                {
                    "service_id": self.service_1.id,
                    "component_id": self.component_11.id,
                    "host_id": host3.id,
                },
            ],
        )

        policy = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component_host())
        policy.user.add(self.user)
        policy.add_object(self.component_21)

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host3))

        policy.apply()

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_21))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host2))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host3))

    def test_parent_policy4provider(self):
        provider, host1, host2 = self.get_hosts_and_provider()
        policy = Policy.objects.create(role=self.object_role_custom_perm_provider_host())
        policy.user.add(self.user)
        policy.add_object(provider)

        self.assertFalse(self.user.has_perm("cm.change_config_of_hostprovider", provider))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host2))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.change_config_of_hostprovider", provider))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host2))

    def test_simple_parent_policy(self):
        policy = Policy.objects.create(role=self.model_role_view_cluster_service_component_perm())
        policy.user.add(self.user)

        self.assertFalse(self.user.has_perm("cm.view_cluster"))
        self.assertFalse(self.user.has_perm("cm.view_clusterobject"))
        self.assertFalse(self.user.has_perm("cm.view_servicecomponent"))

        self.clear_perm_cache(self.user)
        policy.apply()

        self.assertTrue(self.user.has_perm("cm.view_cluster"))
        self.assertTrue(self.user.has_perm("cm.view_clusterobject"))
        self.assertTrue(self.user.has_perm("cm.view_servicecomponent"))

    def test_add_service(self):
        sp_3 = Prototype.obj.create(bundle=self.bundle_1, type="service", name="service_3")

        policy = Policy.objects.create(role=self.object_role_custom_perm_cluster_service())
        policy.user.add(self.user)
        policy.add_object(self.cluster)

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_2))

        service3 = api.add_service_to_cluster(self.cluster, sp_3)

        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", service3))

    def test_add_host(self):
        _, host1, host2 = self.get_hosts_and_provider()
        api.add_host_to_cluster(self.cluster, host1)
        api.add_hc(
            self.cluster,
            [
                {
                    "service_id": self.service_1.id,
                    "component_id": self.component_11.id,
                    "host_id": host1.id,
                },
            ],
        )

        policy = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component_host())
        policy.user.add(self.user)
        policy.add_object(self.cluster)

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host2))

        policy.apply()

        self.assertTrue(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host2))

        api.add_host_to_cluster(self.cluster, host2)

        self.assertTrue(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host2))

    def test_add_hc(self):
        _, host1, host2 = self.get_hosts_and_provider()
        api.add_host_to_cluster(self.cluster, host1)
        api.add_hc(
            self.cluster,
            [
                {
                    "service_id": self.service_1.id,
                    "component_id": self.component_11.id,
                    "host_id": host1.id,
                },
            ],
        )
        policy = Policy.objects.create(role=self.object_role_custom_perm_service_component_host())
        policy.user.add(self.user)
        policy.add_object(self.service_1)

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_12))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host2))

        policy.apply()

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_12))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(self.user.has_perm("cm.change_config_of_host", host2))

        api.add_host_to_cluster(self.cluster, host2)
        api.add_hc(
            self.cluster,
            [
                {
                    "service_id": self.service_1.id,
                    "component_id": self.component_11.id,
                    "host_id": host1.id,
                },
                {
                    "service_id": self.service_1.id,
                    "component_id": self.component_12.id,
                    "host_id": host2.id,
                },
            ],
        )

        self.assertFalse(self.user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(self.user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(self.user.has_perm("cm.change_config_of_servicecomponent", self.component_12))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(self.user.has_perm("cm.change_config_of_host", host2))
