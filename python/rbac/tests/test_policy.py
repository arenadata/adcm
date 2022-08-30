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
from rbac.tests.test_base import BaseTestCase


class PolicyTest(BaseTestCase):  # pylint: disable=too-many-instance-attributes
    """Tests for applying policy with different combination of roles and object"""

    def setUp(self) -> None:
        super().setUp()
        self.user = User.objects.create(username="user", is_active=True, is_superuser=False)
        self.cluster = Cluster.objects.create(name="Cluster_1", prototype=self.clp)
        self.service_1 = ClusterObject.objects.create(cluster=self.cluster, prototype=self.sp_1)
        self.service_2 = ClusterObject.objects.create(cluster=self.cluster, prototype=self.sp_2)
        self.component_11 = ServiceComponent.objects.create(
            cluster=self.cluster, service=self.service_1, prototype=self.cop_11
        )
        self.component_12 = ServiceComponent.objects.create(
            cluster=self.cluster, service=self.service_1, prototype=self.cop_12
        )
        self.component_21 = ServiceComponent.objects.create(
            cluster=self.cluster, service=self.service_2, prototype=self.cop_21
        )

    def get_hosts_and_provider(self):
        provider, _ = HostProvider.objects.get_or_create(name="provider", prototype=self.pp)
        host1 = Host.objects.create(prototype=self.hp, provider=provider, fqdn="host_1")
        host2 = Host.objects.create(prototype=self.hp, provider=provider, fqdn="host_2")
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
        user = self.user

        p = Policy.objects.create(name="MyPolicy", role=self.model_role())
        p.user.add(user)

        self.assertNotIn(self.add_host_perm, user.user_permissions.all())
        self.assertFalse(user.has_perm("cm.add_host"))
        self.clear_perm_cache(user)

        p.apply()
        self.assertIn(self.add_host_perm, user.user_permissions.all())
        self.assertTrue(user.has_perm("cm.add_host"))

        self.clear_perm_cache(user)
        p.apply()
        self.assertTrue(user.has_perm("cm.add_host"))

    def test_model_policy4group(self):
        user = self.user
        group = Group.objects.create(name="group")
        group.user_set.add(user)

        p = Policy.objects.create(name="MyPolicy", role=self.model_role())
        p.group.add(group)

        self.assertNotIn(self.add_host_perm, group.permissions.all())
        self.assertFalse(user.has_perm("cm.add_host"))
        self.clear_perm_cache(user)

        p.apply()
        self.assertIn(self.add_host_perm, group.permissions.all())
        self.assertTrue(user.has_perm("cm.add_host"))

        self.clear_perm_cache(user)
        p.apply()
        self.assertTrue(user.has_perm("cm.add_host"))

    def test_object_policy(self):
        user = self.user
        cluster2 = Cluster.objects.create(name="Cluster_2", prototype=self.clp)
        p = Policy.objects.create(name="MyPolicy", role=self.object_role_view_perm_cluster())
        p.user.add(user)

        self.assertFalse(user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.view_cluster", cluster2))

        p.add_object(self.cluster)
        p.apply()

        self.assertTrue(user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.view_cluster", cluster2))

    def test_object_policy_remove_user(self):
        cluster2 = Cluster.objects.create(name="Cluster_2", prototype=self.clp)
        user = self.user

        p = Policy.objects.create(name="MyPolicy", role=self.object_role())
        p.user.add(user)
        p.add_object(self.cluster)
        self.assertFalse(user.has_perm("cm.view_cluster", self.cluster))

        p.apply()

        self.assertTrue(user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.view_cluster", cluster2))

        p.user.remove(user)
        p.apply()

        self.assertFalse(user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.view_cluster", cluster2))

    def test_object_policy4group(self):
        user = self.user
        cluster2 = Cluster.objects.create(name="Cluster_2", prototype=self.clp)
        group = Group.objects.create(name="group")
        group.user_set.add(user)

        p = Policy.objects.create(name="MyPolicy", role=self.object_role())
        p.group.add(group)

        p.add_object(self.cluster)
        self.assertFalse(user.has_perm("cm.view_cluster", self.cluster))

        p.apply()

        self.assertTrue(user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.view_cluster", cluster2))

    def test_parent_policy4cluster(self):
        user = self.user
        p = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component())
        p.user.add(user)
        p.add_object(self.cluster)

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

        p.apply()

        self.assertTrue(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

    def test_parent_policy4service(self):
        user = self.user
        p = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component())
        p.user.add(user)
        p.add_object(self.service_1)

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

        p.apply()

        self.assertTrue(user.has_perm("cm.view_cluster", self.cluster))

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

    def test_parent_policy4service2(self):
        user = self.user
        p = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component())
        p.user.add(user)
        p.add_object(self.service_2)

        self.assertFalse(user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

        p.apply()

        self.assertTrue(user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

    def test_parent_policy4component(self):
        user = self.user
        p = Policy.objects.create(role=self.object_role_custom_perm_cluster_service_component())
        p.user.add(user)
        p.add_object(self.component_11)
        self.assertFalse(user.has_perm("cm.view_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.view_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

        p.apply()

        self.assertTrue(user.has_perm("cm.view_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.view_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))

    def test_parent_policy4host_in_cluster(self):
        user = self.user
        provider, host1, host2 = self.get_hosts_and_provider()
        host3 = Host.objects.create(provider=provider, prototype=self.hp, fqdn="host_3")
        api.add_host_to_cluster(self.cluster, host1)
        api.add_host_to_cluster(self.cluster, host2)
        p = Policy.objects.create(role=self.object_role_custom_perm_cluster_host())
        p.user.add(user)
        p.add_object(self.cluster)

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host2))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host3))

        p.apply()

        self.assertTrue(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host2))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host3))

    def test_parent_policy4host_in_service(self):
        user = self.user
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
        p = Policy.objects.create(
            role=self.object_role_custom_perm_cluster_service_component_host()
        )
        p.user.add(user)
        p.add_object(self.service_1)

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host2))

        p.apply()

        self.assertFalse(user.has_perm("cm.change_confing_of_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host2))

    def test_parent_policy4host_in_component(self):
        user = self.user
        provider, host1, host2 = self.get_hosts_and_provider()
        host3 = Host.objects.create(provider=provider, prototype=self.hp, fqdn="host_3")
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

        p = Policy.objects.create(
            role=self.object_role_custom_perm_cluster_service_component_host()
        )
        p.user.add(user)
        p.add_object(self.component_21)

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host2))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host3))

        p.apply()

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_21))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host2))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host3))

    def test_parent_policy4provider(self):
        user = self.user
        provider, host1, host2 = self.get_hosts_and_provider()
        p = Policy.objects.create(role=self.object_role_custom_perm_provider_host())
        p.user.add(user)
        p.add_object(provider)

        self.assertFalse(user.has_perm("cm.change_config_of_hostprovider", provider))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host2))

        p.apply()

        self.assertTrue(user.has_perm("cm.change_config_of_hostprovider", provider))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host2))

    def test_simple_parent_policy(self):
        user = self.user
        p = Policy.objects.create(role=self.model_role_view_cluster_service_component_perm())
        p.user.add(user)

        self.assertFalse(user.has_perm("cm.view_cluster"))
        self.assertFalse(user.has_perm("cm.view_clusterobject"))
        self.assertFalse(user.has_perm("cm.view_servicecomponent"))

        self.clear_perm_cache(user)
        p.apply()

        self.assertTrue(user.has_perm("cm.view_cluster"))
        self.assertTrue(user.has_perm("cm.view_clusterobject"))
        self.assertTrue(user.has_perm("cm.view_servicecomponent"))

    def test_add_service(self):
        user = self.user
        sp_3 = Prototype.obj.create(bundle=self.bundle_1, type="service", name="service_3")

        p = Policy.objects.create(role=self.object_role_custom_perm_cluster_service())
        p.user.add(user)
        p.add_object(self.cluster)

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_2))

        p.apply()

        self.assertTrue(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_2))

        service3 = api.add_service_to_cluster(self.cluster, sp_3)
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", service3))

    def test_add_host(self):
        user = self.user
        _, host1, host2 = self.get_hosts_and_provider()
        api.add_host_to_cluster(self.cluster, host1)
        api.add_hc(
            self.cluster,
            [
                {
                    "service_id": self.service_1.id,
                    "component_id": self.component_11.id,
                    "host_id": host1.id,
                }
            ],
        )

        p = Policy.objects.create(
            role=self.object_role_custom_perm_cluster_service_component_host()
        )
        p.user.add(user)
        p.add_object(self.cluster)

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host2))

        p.apply()

        self.assertTrue(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host2))

        api.add_host_to_cluster(self.cluster, host2)

        self.assertTrue(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host2))

    def test_add_hc(self):
        user = self.user
        _, host1, host2 = self.get_hosts_and_provider()
        api.add_host_to_cluster(self.cluster, host1)
        api.add_hc(
            self.cluster,
            [
                {
                    "service_id": self.service_1.id,
                    "component_id": self.component_11.id,
                    "host_id": host1.id,
                }
            ],
        )
        p = Policy.objects.create(role=self.object_role_custom_perm_service_component_host())
        p.user.add(user)
        p.add_object(self.service_1)

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertFalse(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertFalse(user.has_perm("cm.change_config_of_servicecomponent", self.component_12))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host2))

        p.apply()

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_12))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host1))
        self.assertFalse(user.has_perm("cm.change_config_of_host", host2))

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

        self.assertFalse(user.has_perm("cm.change_config_of_cluster", self.cluster))
        self.assertTrue(user.has_perm("cm.change_config_of_clusterobject", self.service_1))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_11))
        self.assertTrue(user.has_perm("cm.change_config_of_servicecomponent", self.component_12))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host1))
        self.assertTrue(user.has_perm("cm.change_config_of_host", host2))
