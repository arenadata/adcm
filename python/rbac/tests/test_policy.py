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

# pylint: disable=too-many-lines

from pathlib import Path
from unittest.mock import patch

from cm import api
from cm.models import (
    Bundle,
    Cluster,
    ClusterObject,
    ConfigLog,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from django.conf import settings
from django.db.models import ObjectDoesNotExist
from django.urls import reverse
from rbac.models import Group, Policy, User
from rbac.tests.test_base import RBACBaseTestCase
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


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


class TestPolicyWithClusterAdminRole(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        files_dir = settings.BASE_DIR / "python" / "rbac" / "tests" / "files"
        provider_bundle_filename = files_dir / "provider.tar"
        cluster_bundle_filename = files_dir / "test_cluster_for_cluster_admin_role.tar"

        provider = self._make_adcm_entity(
            entity_type=ObjectType.PROVIDER, bundle_filename=provider_bundle_filename, name="Test Provider"
        )
        self.cluster = self._make_adcm_entity(
            entity_type=ObjectType.CLUSTER, bundle_filename=cluster_bundle_filename, name="Test Cluster"
        )

        self.service_6_proto = Prototype.objects.get(
            bundle=Bundle.objects.get(name="test_cluster_for_cluster_admin_role"),
            name="service_6_manual_add",
            type=ObjectType.SERVICE,
        )

        self.host_pks = self._make_hosts(num=5, provider_id=provider.pk, cluster_id=self.cluster.pk)
        self.service_pks = self._make_services(cluster_id=self.cluster.pk)
        self.assertEqual(len(self.host_pks), len(self.service_pks))

        self.component_pks = self._save_hc_map(host_pks=self.host_pks, service_pks=self.service_pks)

    def _save_hc_map(self, host_pks: list[int], service_pks: list[int]) -> list[int]:
        component_pks = []
        hc_data = []

        for host_pk, service_pk in zip(host_pks, service_pks):
            for component in ServiceComponent.objects.filter(service=ClusterObject.objects.get(pk=service_pk)):
                component_pks.append(component.pk)
                hc_data.append({"component_id": component.pk, "host_id": host_pk, "service_id": service_pk})

        response: Response = self.client.post(
            path=reverse(viewname="host-component", kwargs={"cluster_id": self.cluster.pk}),
            data={"cluster_id": self.cluster.pk, "hc": hc_data},
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return component_pks

    def _make_adcm_entity(self, entity_type: ObjectType, bundle_filename: Path, name: str) -> Cluster | HostProvider:
        if entity_type == ObjectType.CLUSTER:
            model = Cluster
            viewname = "cluster"
        elif entity_type == ObjectType.PROVIDER:
            model = HostProvider
            viewname = "provider"
        else:
            raise NotImplementedError

        bundle = self.upload_and_load_bundle(path=bundle_filename)

        response: Response = self.client.post(
            path=reverse(viewname=viewname),
            data={
                "prototype_id": Prototype.objects.get(bundle=bundle, type=entity_type).pk,
                "name": name,
                "display_name": name,
                "bundle_id": bundle.pk,
            },
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return model.objects.get(pk=response.json()["id"])

    def _get_role_request_data(self, role_display_name: str) -> dict | None:
        response: Response = self.client.get(
            path=reverse(viewname="rbac:role-list"),
            data={"ordering": "name", "type": "role", "view": "interface"},
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        target_role_data = None
        for role_data in response.json()["results"]:
            if role_data["display_name"] == role_display_name:
                target_role_data = role_data
                break

        return target_role_data

    def _get_user_request_data(self, username: str) -> dict | None:
        response: Response = self.client.get(
            path=reverse(viewname="rbac:user-list"),
            data={"ordering": "username", "view": "interface"},
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        target_user_data = None
        for user_data in response.json()["results"]:
            if user_data["username"] == username:
                target_user_data = user_data
                break

        return target_user_data

    def _apply_policy(self, role_display_name: str, username: str) -> None:
        role_data = self._get_role_request_data(role_display_name=role_display_name)
        self.assertIsNotNone(role_data)

        user_data = self._get_user_request_data(username=username)
        self.assertIsNotNone(user_data)

        policy_request_data = {
            "name": "test_policy_cluster_admin",
            "role": {"id": role_data["id"]},
            "user": [
                {"id": user_data["id"]},
            ],
            "group": [],
            "object": [
                {"name": self.cluster.name, "type": "cluster", "id": self.cluster.pk},
            ],
        }
        response: Response = self.client.post(
            path=reverse(viewname="rbac:policy-list"),
            data=policy_request_data,
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def _make_hosts(self, num: int, provider_id: int, cluster_id: int | None = None) -> list[int]:
        host_pks = []

        for host_num in range(num):
            fqdn = f"host-{host_num}"

            response: Response = self.client.post(
                path=reverse(viewname="host", kwargs={"provider_id": provider_id}),
                data={
                    "fqdn": fqdn,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            host_id = response.json()["id"]
            host_pks.append(host_id)

            if not cluster_id:
                continue

            response: Response = self.client.post(
                path=reverse(viewname="host", kwargs={"cluster_id": cluster_id}),
                data={
                    "host_id": host_id,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

        return host_pks

    def _make_services(self, cluster_id: int) -> list[int]:
        service_pks = []

        service_proto_pks = (
            Prototype.objects.filter(
                bundle=Bundle.objects.get(name="test_cluster_for_cluster_admin_role"), type=ObjectType.SERVICE
            )
            .exclude(pk=self.service_6_proto.pk)
            .order_by("name")
            .values_list("pk", flat=True)
        )
        for service_proto_pk in service_proto_pks:
            response = self.client.post(
                path=reverse(viewname="service", kwargs={"cluster_id": cluster_id}),
                data={
                    "prototype_id": service_proto_pk,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            service_pks.append(response.json()["id"])

        return service_pks

    def test_view_perm_for_cluster_and_all_descendants_success(self):
        # pylint: disable=too-many-statements
        with self.no_rights_user_logged_in:
            response: Response = self.client.get(
                path=reverse(viewname="cluster-details", kwargs={"cluster_id": self.cluster.pk}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response: Response = self.client.get(
                path=reverse(viewname="service-details", kwargs={"service_id": self.service_pks[0]}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response: Response = self.client.get(
                path=reverse(viewname="component-details", kwargs={"component_id": self.component_pks[0]}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response: Response = self.client.get(
                path=reverse(viewname="host-details", kwargs={"host_id": self.host_pks[0]}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response: Response = self.client.get(
                path=reverse(viewname="host", kwargs={"cluster_id": self.cluster.pk}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response: Response = self.client.get(
                path=reverse(
                    viewname="config-current",
                    kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster", "version": "current"},
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response: Response = self.client.get(
                path=reverse(
                    viewname="config-current",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service_pks[0],
                        "object_type": "service",
                        "version": "current",
                    },
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response: Response = self.client.get(
                path=reverse(
                    viewname="config-current",
                    kwargs={"component_id": self.component_pks[0], "object_type": "component", "version": "current"},
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response: Response = self.client.get(
                path=reverse(
                    viewname="object-action", kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster"}
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json(), [])

            response: Response = self.client.get(
                path=reverse(
                    viewname="object-action", kwargs={"service_id": self.service_pks[0], "object_type": "service"}
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json(), [])

            response: Response = self.client.get(
                path=reverse(
                    viewname="object-action", kwargs={"component_id": self.component_pks[0], "object_type": "component"}
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json(), [])

        self._apply_policy(role_display_name="Cluster Administrator", username=self.no_rights_user_username)

        with self.no_rights_user_logged_in:
            response: Response = self.client.get(
                path=reverse(viewname="cluster-details", kwargs={"cluster_id": self.cluster.pk}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response: Response = self.client.get(
                path=reverse(viewname="service-details", kwargs={"service_id": self.service_pks[0]}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response: Response = self.client.get(
                path=reverse(viewname="component-details", kwargs={"component_id": self.component_pks[0]}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response: Response = self.client.get(
                path=reverse(viewname="host-details", kwargs={"host_id": self.host_pks[0]}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response: Response = self.client.get(
                path=reverse(viewname="host", kwargs={"cluster_id": self.cluster.pk}),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response: Response = self.client.get(
                path=reverse(
                    viewname="config-current",
                    kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster", "version": "current"},
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response: Response = self.client.get(
                path=reverse(
                    viewname="config-current",
                    kwargs={
                        "cluster_id": self.cluster.pk,
                        "service_id": self.service_pks[0],
                        "object_type": "service",
                        "version": "current",
                    },
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response: Response = self.client.get(
                path=reverse(
                    viewname="config-current",
                    kwargs={"component_id": self.component_pks[0], "object_type": "component", "version": "current"},
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response: Response = self.client.get(
                path=reverse(
                    viewname="object-action", kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster"}
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIsInstance(response.json(), list)
            self.assertTrue(len(response.json()) > 0)

            response: Response = self.client.get(
                path=reverse(
                    viewname="object-action", kwargs={"service_id": self.service_pks[0], "object_type": "service"}
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIsInstance(response.json(), list)
            self.assertTrue(len(response.json()) > 0)

            response: Response = self.client.get(
                path=reverse(
                    viewname="object-action", kwargs={"component_id": self.component_pks[0], "object_type": "component"}
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIsInstance(response.json(), list)
            self.assertTrue(len(response.json()) > 0)

    def test_edit_perm_for_cluster_and_all_descendants_success(self):
        initial_hc_count = HostComponent.objects.count()

        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="host-component", kwargs={"cluster_id": self.cluster.pk}),
                data={
                    "cluster_id": self.cluster.pk,
                    "hc": [
                        {
                            "component_id": self.component_pks[0],
                            "host_id": self.host_pks[0],
                            "service_id": self.service_pks[0],
                        }
                    ],
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history", kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster"}
                ),
                data={"attr": {}, "config": {"float": 3.3}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history",
                    kwargs={"cluster_id": self.cluster.pk, "service_id": self.service_pks[0], "object_type": "service"},
                ),
                data={"attr": {}, "config": {"float": 3.3}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history",
                    kwargs={"component_id": self.component_pks[0], "object_type": "component"},
                ),
                data={"attr": {}, "config": {"float": 3.3}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history",
                    kwargs={"host_id": self.host_pks[0], "object_type": "host"},
                ),
                data={"attr": {}, "config": {"string": "new_srting"}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history",
                    kwargs={"cluster_id": self.cluster.pk, "host_id": self.host_pks[0], "object_type": "host"},
                ),
                data={"attr": {}, "config": {"string": "new_srting"}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            response = self.client.post(
                path=reverse(viewname="service", kwargs={"cluster_id": self.cluster.pk}),
                data={
                    "prototype_id": self.service_6_proto.pk,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

            response = self.client.delete(
                path=reverse(
                    viewname="service-details",
                    kwargs={"cluster_id": self.cluster.pk, "service_id": self.service_pks[-1]},
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response = self.client.post(
                path=reverse(viewname="service-maintenance-mode", kwargs={"service_id": self.service_pks[0]}),
                data={
                    "maintenance_mode": MaintenanceMode.ON,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response = self.client.post(
                path=reverse(viewname="component-maintenance-mode", kwargs={"component_id": self.component_pks[0]}),
                data={
                    "maintenance_mode": MaintenanceMode.ON,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response = self.client.post(
                path=reverse(viewname="host-maintenance-mode", kwargs={"host_id": self.host_pks[0]}),
                data={
                    "maintenance_mode": MaintenanceMode.ON,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._apply_policy(role_display_name="Cluster Administrator", username=self.no_rights_user_username)

        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="host-component", kwargs={"cluster_id": self.cluster.pk}),
                data={
                    "cluster_id": self.cluster.pk,
                    "hc": [
                        {
                            "component_id": self.component_pks[0],
                            "host_id": self.host_pks[0],
                            "service_id": self.service_pks[0],
                        }
                    ],
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertTrue(initial_hc_count != HostComponent.objects.count())

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history", kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster"}
                ),
                data={"attr": {}, "config": {"float": 3.3}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history",
                    kwargs={"cluster_id": self.cluster.pk, "service_id": self.service_pks[0], "object_type": "service"},
                ),
                data={"attr": {}, "config": {"float": 3.3}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history",
                    kwargs={"component_id": self.component_pks[0], "object_type": "component"},
                ),
                data={"attr": {}, "config": {"float": 3.3}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history",
                    kwargs={"host_id": self.host_pks[0], "object_type": "host"},
                ),
                data={"attr": {}, "config": {"string": "new_srting"}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            response: Response = self.client.post(
                path=reverse(
                    viewname="config-history",
                    kwargs={"cluster_id": self.cluster.pk, "host_id": self.host_pks[0], "object_type": "host"},
                ),
                data={"attr": {}, "config": {"string": "new_srting"}},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            response = self.client.post(
                path=reverse(viewname="service", kwargs={"cluster_id": self.cluster.pk}),
                data={
                    "prototype_id": self.service_6_proto.pk,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            response = self.client.delete(
                path=reverse(
                    viewname="service-details",
                    kwargs={"cluster_id": self.cluster.pk, "service_id": self.service_pks[-1]},
                ),
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

            response = self.client.post(
                path=reverse(viewname="service-maintenance-mode", kwargs={"service_id": self.service_pks[0]}),
                data={
                    "maintenance_mode": MaintenanceMode.ON,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.post(
                path=reverse(viewname="component-maintenance-mode", kwargs={"component_id": self.component_pks[0]}),
                data={
                    "maintenance_mode": MaintenanceMode.ON,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.post(
                path=reverse(viewname="host-maintenance-mode", kwargs={"host_id": self.host_pks[0]}),
                data={
                    "maintenance_mode": MaintenanceMode.ON,
                },
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)


class TestPolicyWithProviderAdminRole(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.new_user = self._get_new_user()
        self.provider = self._get_provider()
        self._create_policy()

    def _get_provider(self) -> HostProvider:
        bundle = self.upload_and_load_bundle(
            path=settings.BASE_DIR / "python" / "rbac" / "tests" / "files" / "provider_2.tar",
        )

        response: Response = self.client.post(
            path=reverse(viewname="provider"),
            data={
                "prototype_id": Prototype.objects.get(bundle=bundle, type=ObjectType.PROVIDER).pk,
                "name": "Test Provider",
                "display_name": "Test Provider",
                "bundle_id": bundle.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return HostProvider.objects.get(pk=response.json()["id"])

    def _get_new_user(self) -> User:
        response: Response = self.client.post(
            path=reverse(viewname="rbac:user-list"),
            data={"username": "new_user", "password": "new_user_password"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return User.objects.get(pk=response.json()["id"])

    def _get_role_pk(self) -> int:
        response: Response = self.client.get(
            path=reverse(viewname="rbac:role-list"),
            data={"ordering": "name", "type": "role", "view": "interface"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        return [
            role_data["id"] for role_data in response.json()["results"] if role_data["name"] == "Provider Administrator"
        ][0]

    def _create_policy(self) -> None:
        response: Response = self.client.post(
            path=reverse(viewname="rbac:policy-list"),
            data={
                "name": "test_policy_provider_admin",
                "role": {"id": self._get_role_pk()},
                "user": [{"id": self.new_user.pk}],
                "group": [],
                "object": [{"name": self.provider.name, "type": "provider", "id": self.provider.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def _retrieve_provider_action(self) -> Response:
        response: Response = self.client.get(
            path=reverse(viewname="object-action", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        return response

    def _create_host(self) -> Host:
        response: Response = self.client.post(
            path=reverse("host", kwargs={"provider_id": self.provider.pk}),
            data={"fqdn": "test-host"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return Host.objects.get(pk=response.data["id"])

    def _retrieve_host_action(self, host_pk: int) -> Response:
        response: Response = self.client.get(
            path=reverse(viewname="object-action", kwargs={"host_id": host_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        return response

    def test_policy_add_required_perms_success(self):
        required_perms = {perm.codename for perm in self.new_user.user_permissions.all()}
        required_perms.update({perm.permission.codename for perm in self.new_user.userobjectpermission_set.all()})

        self.assertEqual(
            required_perms,
            {
                "delete_bundle",
                "add_groupconfig",
                "change_objectconfig",
                "add_bundle",
                "change_groupconfig",
                "add_configlog",
                "delete_groupconfig",
                "add_prototype",
                "change_bundle",
                "change_configlog",
                "add_host",
                "view_configlog",
                "view_hostprovider",
                "do_upgrade_of_hostprovider",
                "change_config_of_hostprovider",
                "view_action",
                "view_upgrade_of_hostprovider",
                "view_objectconfig",
                "add_host_to_hostprovider",
                "run_action_bd938c688f49b77c7fc537c6b9222e2c97ebddd63076b87f2feaec66fb9c05d0",
            },
        )

    def test_retrieve_provider_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="provider-details", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["name"], self.provider.name)

    def test_retrieve_provider_config_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="object-config", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_update_provider_config_success(self):
        new_string = "new_string"

        response: Response = self.client.post(
            path=reverse(viewname="config-history", kwargs={"provider_id": self.provider.pk}),
            data={"config": {"string": new_string}},
            content_type=APPLICATION_JSON,
        )

        self.provider.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.provider.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(config_log.config["string"], new_string)

    def test_retrieve_provider_actions_success(self):
        self._retrieve_provider_action()

    def test_run_provider_actions_success(self):
        response: Response = self._retrieve_provider_action()

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="run-task",
                    kwargs={"provider_id": self.provider.pk, "action_id": response.data[0]["id"]},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_create_host_success(self):
        self._create_host()

    def test_retrieve_host_success(self):
        host: Host = self._create_host()
        response: Response = self.client.get(path=reverse("host-details", kwargs={"host_id": host.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["id"], host.pk)

    def test_retrieve_host_config_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="object-config", kwargs={"host_id": self._create_host().pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_update_host_config_success(self):
        host: Host = self._create_host()
        new_string = "new_string"

        response: Response = self.client.post(
            path=reverse(viewname="config-history", kwargs={"host_id": host.pk}),
            data={"config": {"string": new_string}},
            content_type=APPLICATION_JSON,
        )

        host.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=host.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(config_log.config["string"], new_string)

    def test_retrieve_host_actions_success(self):
        self._retrieve_host_action(host_pk=self._create_host().pk)

    def test_run_host_actions_success(self):
        host: Host = self._create_host()
        response: Response = self._retrieve_host_action(host_pk=host.pk)

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="run-task",
                    kwargs={"host_id": host.pk, "action_id": response.data[0]["id"]},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_delete_host_success(self):
        host: Host = self._create_host()

        response: Response = self.client.delete(path=reverse("host-details", kwargs={"host_id": host.pk}))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        with self.assertRaises(ObjectDoesNotExist):
            host.refresh_from_db()
