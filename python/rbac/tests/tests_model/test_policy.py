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

from adwp_base.errors import AdwpEx
from tests_base import BaseTestCase

from cm import api
from cm.models import Bundle, Prototype, Action
from rbac.models import Role, Policy


class CreateIssueTest(BaseTestCase):
    """Tests for `cm.issue.create_issues()`"""

    def setUp(self) -> None:
        pass

    @staticmethod
    def clear_perm_cache(user):
        if hasattr(user, '_perm_cache'):
            delattr(user, '_perm_cache')
        if hasattr(user, '_user_perm_cache'):
            delattr(user, '_user_perm_cache')
        if hasattr(user, '_group_perm_cache'):
            delattr(user, '_group_perm_cache')

    def test_model_policy(self, user, model_role, add_host_perm):

        model_role.permissions.add(add_host_perm)

        p = Policy.objects.create(name='MyPolicy', role=model_role)
        p.user.add(user)

        assert add_host_perm not in user.user_permissions.all()
        assert not user.has_perm('cm.add_host')
        self.clear_perm_cache(user)

        p.apply()
        assert add_host_perm in user.user_permissions.all()
        assert user.has_perm('cm.add_host')

        self.clear_perm_cache(user)
        p.apply()
        assert user.has_perm('cm.add_host')

    def test_model_policy4group(self, user, group, model_role, add_host_perm):
        group.user_set.add(user)
        model_role.permissions.add(add_host_perm)

        p = Policy.objects.create(name='MyPolicy', role=model_role)
        p.group.add(group)

        assert add_host_perm not in group.permissions.all()
        assert not user.has_perm('cm.add_host')
        self.clear_perm_cache(user)

        p.apply()
        assert add_host_perm in group.permissions.all()
        assert user.has_perm('cm.add_host')

        self.clear_perm_cache(user)
        p.apply()
        assert user.has_perm('cm.add_host')

    @pytest.mark.django_db
    def test_object_policy(self, user, cluster1, cluster2, object_role_view_perm_cluster):

        p = Policy.objects.create(name='MyPolicy', role=object_role_view_perm_cluster)
        p.user.add(user)

        assert not user.has_perm('cm.view_cluster', cluster1)
        assert not user.has_perm('cm.view_cluster', cluster2)

        p.add_object(cluster1)
        p.apply()

        assert user.has_perm('cm.view_cluster', cluster1)
        assert not user.has_perm('cm.view_cluster', cluster2)

    @pytest.mark.django_db
    def test_object_policy_remove_user(
        self, user, cluster1, cluster2, object_role, view_cluster_perm
    ):

        object_role.permissions.add(view_cluster_perm)

        p = Policy.objects.create(name='MyPolicy', role=object_role)
        p.user.add(user)
        p.add_object(cluster1)
        assert not user.has_perm('cm.view_cluster', cluster1)

        p.apply()

        assert user.has_perm('cm.view_cluster', cluster1)
        assert not user.has_perm('cm.view_cluster', cluster2)

        p.user.remove(user)
        p.apply()

        assert not user.has_perm('cm.view_cluster', cluster1)
        assert not user.has_perm('cm.view_cluster', cluster2)

    @pytest.mark.django_db
    def test_object_policy4group(
        self, user, group, cluster1, cluster2, object_role, view_cluster_perm
    ):
        group.user_set.add(user)

        object_role.permissions.add(view_cluster_perm)

        p = Policy.objects.create(name='MyPolicy', role=object_role)
        p.group.add(group)

        p.add_object(cluster1)
        assert not user.has_perm('cm.view_cluster', cluster1)

        p.apply()

        assert user.has_perm('cm.view_cluster', cluster1)
        assert not user.has_perm('cm.view_cluster', cluster2)

    @pytest.mark.django_db
    def test_parent_policy4cluster(
        self,
        user,
        cluster1,
        service1,
        service2,
        component11,
        component21,
        object_role_custom_perm_cluster_service_component,
    ):

        p = Policy.objects.create(role=object_role_custom_perm_cluster_service_component)
        p.user.add(user)
        p.add_object(cluster1)

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component21)

        p.apply()

        assert user.has_perm('cm.change_config_of_cluster', cluster1)
        assert user.has_perm('cm.change_config_of_clusterobject', service1)
        assert user.has_perm('cm.change_config_of_clusterobject', service2)
        assert user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert user.has_perm('cm.change_config_of_servicecomponent', component21)

    @pytest.mark.django_db
    def test_parent_policy4service(
        self,
        user,
        cluster1,
        service1,
        service2,
        component11,
        component21,
        object_role_custom_perm_cluster_service_component,
    ):
        p = Policy.objects.create(role=object_role_custom_perm_cluster_service_component)
        p.user.add(user)
        p.add_object(service1)

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component21)

        p.apply()

        assert user.has_perm('cm.view_cluster', cluster1)

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component21)

    @pytest.mark.django_db
    def test_parent_policy4service2(
        self,
        user,
        cluster1,
        service1,
        service2,
        component11,
        component21,
        object_role_custom_perm_cluster_service_component,
    ):
        p = Policy.objects.create(role=object_role_custom_perm_cluster_service_component)
        p.user.add(user)
        p.add_object(service2)

        assert not user.has_perm('cm.view_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component21)

        p.apply()

        assert user.has_perm('cm.view_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert user.has_perm('cm.change_config_of_clusterobject', service2)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert user.has_perm('cm.change_config_of_servicecomponent', component21)

    @pytest.mark.django_db
    def test_parent_policy4component(
        self,
        user,
        cluster1,
        service1,
        service2,
        component11,
        component21,
        object_role_custom_perm_cluster_service_component,
    ):
        p = Policy.objects.create(role=object_role_custom_perm_cluster_service_component)
        p.user.add(user)
        p.add_object(component11)
        assert not user.has_perm('cm.view_cluster', cluster1)
        assert not user.has_perm('cm.view_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component21)

        p.apply()

        assert user.has_perm('cm.view_cluster', cluster1)
        assert user.has_perm('cm.view_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component21)

    @pytest.mark.django_db
    def test_parent_policy4host_in_cluster(
        self, user, cluster1, host1, host2, host3, object_role_custom_perm_cluster_host
    ):
        api.add_host_to_cluster(cluster1, host1)
        api.add_host_to_cluster(cluster1, host2)
        p = Policy.objects.create(role=object_role_custom_perm_cluster_host)
        p.user.add(user)
        p.add_object(cluster1)

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_host', host1)
        assert not user.has_perm('cm.change_config_of_host', host2)
        assert not user.has_perm('cm.change_config_of_host', host3)

        p.apply()

        assert user.has_perm('cm.change_config_of_cluster', cluster1)
        assert user.has_perm('cm.change_config_of_host', host1)
        assert user.has_perm('cm.change_config_of_host', host2)
        assert not user.has_perm('cm.change_config_of_host', host3)

    @pytest.mark.django_db
    # pylint: disable=too-many-arguments
    def test_parent_policy4host_in_service(
        self,
        user,
        cluster1,
        service1,
        service2,
        component11,
        component21,
        host1,
        host2,
        object_role_custom_perm_cluster_service_component_host,
    ):
        api.add_host_to_cluster(cluster1, host1)
        api.add_host_to_cluster(cluster1, host2)
        api.add_hc(
            cluster1,
            [
                {"service_id": service1.id, "component_id": component11.id, "host_id": host1.id},
                {"service_id": service2.id, "component_id": component21.id, "host_id": host2.id},
            ],
        )
        p = Policy.objects.create(role=object_role_custom_perm_cluster_service_component_host)
        p.user.add(user)
        p.add_object(service1)

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component21)
        assert not user.has_perm('cm.change_config_of_host', host1)
        assert not user.has_perm('cm.change_config_of_host', host2)

        p.apply()

        assert not user.has_perm('cm.change_confing_of_cluster', cluster1)
        assert user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component21)
        assert user.has_perm('cm.change_config_of_host', host1)
        assert not user.has_perm('cm.change_config_of_host', host2)

    @pytest.mark.django_db
    # pylint: disable=too-many-arguments
    def test_parent_policy4host_in_component(
        self,
        user,
        cluster1,
        service1,
        service2,
        component11,
        component21,
        host1,
        host2,
        host3,
        object_role_custom_perm_cluster_service_component_host,
    ):
        api.add_host_to_cluster(cluster1, host1)
        api.add_host_to_cluster(cluster1, host2)
        api.add_host_to_cluster(cluster1, host3)
        api.add_hc(
            cluster1,
            [
                {'service_id': service2.id, 'component_id': component21.id, 'host_id': host1.id},
                {'service_id': service2.id, 'component_id': component21.id, 'host_id': host2.id},
                {'service_id': service1.id, 'component_id': component11.id, 'host_id': host3.id},
            ],
        )

        p = Policy.objects.create(role=object_role_custom_perm_cluster_service_component_host)
        p.user.add(user)
        p.add_object(component21)

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component21)
        assert not user.has_perm('cm.change_config_of_host', host1)
        assert not user.has_perm('cm.change_config_of_host', host2)
        assert not user.has_perm('cm.change_config_of_host', host3)

        p.apply()

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert user.has_perm('cm.change_config_of_servicecomponent', component21)
        assert user.has_perm('cm.change_config_of_host', host1)
        assert user.has_perm('cm.change_config_of_host', host2)
        assert not user.has_perm('cm.change_config_of_host', host3)

    @pytest.mark.django_db
    def test_parent_policy4provider(
        self, user, provider, host1, host2, host3, object_role_custom_perm_provider_host
    ):
        p = Policy.objects.create(role=object_role_custom_perm_provider_host)
        p.user.add(user)
        p.add_object(provider)

        assert not user.has_perm('cm.change_config_of_hostprovider', provider)
        assert not user.has_perm('cm.change_config_of_host', host1)
        assert not user.has_perm('cm.change_config_of_host', host2)
        assert not user.has_perm('cm.change_config_of_host', host3)

        p.apply()

        assert user.has_perm('cm.change_config_of_hostprovider', provider)
        assert user.has_perm('cm.change_config_of_host', host1)
        assert user.has_perm('cm.change_config_of_host', host2)
        assert user.has_perm('cm.change_config_of_host', host3)

    @pytest.mark.django_db
    def test_simple_parent_policy(self, user, model_role_view_cluster_service_component_perm):

        p = Policy.objects.create(role=model_role_view_cluster_service_component_perm)
        p.user.add(user)

        assert not user.has_perm('cm.view_cluster')
        assert not user.has_perm('cm.view_clusterobject')
        assert not user.has_perm('cm.view_servicecomponent')

        self.clear_perm_cache(user)
        p.apply()

        assert user.has_perm('cm.view_cluster')
        assert user.has_perm('cm.view_clusterobject')
        assert user.has_perm('cm.view_servicecomponent')

    @pytest.mark.django_db
    def test_add_service(
        self, user, cluster1, service1, service2, object_role_custom_perm_cluster_service
    ):
        sp3 = Prototype.obj.create(bundle=self.bundle1, type='service', name='service_3')

        p = Policy.objects.create(role=object_role_custom_perm_cluster_service)
        p.user.add(user)
        p.add_object(cluster1)

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service2)

        p.apply()

        assert user.has_perm('cm.change_config_of_cluster', cluster1)
        assert user.has_perm('cm.change_config_of_clusterobject', service1)
        assert user.has_perm('cm.change_config_of_clusterobject', service2)

        service3 = api.add_service_to_cluster(cluster1, sp3)
        assert user.has_perm('cm.change_config_of_clusterobject', service3)

    @pytest.mark.django_db
    def test_add_host(
        self,
        user,
        cluster1,
        service1,
        component11,
        host1,
        host2,
        object_role_custom_perm_cluster_service_component_host,
    ):
        api.add_host_to_cluster(cluster1, host1)
        api.add_hc(
            cluster1,
            [{'service_id': service1.id, 'component_id': component11.id, 'host_id': host1.id}],
        )

        p = Policy.objects.create(role=object_role_custom_perm_cluster_service_component_host)
        p.user.add(user)
        p.add_object(cluster1)

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_host', host1)
        assert not user.has_perm('cm.change_config_of_host', host2)

        p.apply()

        assert user.has_perm('cm.change_config_of_cluster', cluster1)
        assert user.has_perm('cm.change_config_of_clusterobject', service1)
        assert user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert user.has_perm('cm.change_config_of_host', host1)
        assert not user.has_perm('cm.change_config_of_host', host2)

        api.add_host_to_cluster(cluster1, host2)

        assert user.has_perm('cm.change_config_of_cluster', cluster1)
        assert user.has_perm('cm.change_config_of_clusterobject', service1)
        assert user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert user.has_perm('cm.change_config_of_host', host1)
        assert user.has_perm('cm.change_config_of_host', host2)

    @pytest.mark.django_db
    # pylint: disable=too-many-arguments
    def test_add_hc(
        self,
        user,
        cluster1,
        service1,
        component11,
        component12,
        host1,
        host2,
        object_role_custom_perm_service_component_host,
    ):
        api.add_host_to_cluster(cluster1, host1)
        api.add_hc(
            cluster1,
            [{'service_id': service1.id, 'component_id': component11.id, 'host_id': host1.id}],
        )
        p = Policy.objects.create(role=object_role_custom_perm_service_component_host)
        p.user.add(user)
        p.add_object(service1)

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert not user.has_perm('cm.change_config_of_clusterobject', service1)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert not user.has_perm('cm.change_config_of_servicecomponent', component12)
        assert not user.has_perm('cm.change_config_of_host', host1)
        assert not user.has_perm('cm.change_config_of_host', host2)

        p.apply()

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert user.has_perm('cm.change_config_of_clusterobject', service1)
        assert user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert user.has_perm('cm.change_config_of_servicecomponent', component12)
        assert user.has_perm('cm.change_config_of_host', host1)
        assert not user.has_perm('cm.change_config_of_host', host2)

        api.add_host_to_cluster(cluster1, host2)
        api.add_hc(
            cluster1,
            [
                {'service_id': service1.id, 'component_id': component11.id, 'host_id': host1.id},
                {"service_id": service1.id, "component_id": component12.id, "host_id": host2.id},
            ],
        )

        assert not user.has_perm('cm.change_config_of_cluster', cluster1)
        assert user.has_perm('cm.change_config_of_clusterobject', service1)
        assert user.has_perm('cm.change_config_of_servicecomponent', component11)
        assert user.has_perm('cm.change_config_of_servicecomponent', component12)
        assert user.has_perm('cm.change_config_of_host', host1)
        assert user.has_perm('cm.change_config_of_host', host2)

    @pytest.mark.django_db
    def test_object_filter(self):
        r = Role(
            name='view',
            module_name='rbac.roles',
            class_name='ObjectRole',
            init_params={
                'app_name': 'cm',
                'model': 'Bundle',
                'filter': {'name': 'Hadoop'},
            },
        )
        r.save()

        b1 = Bundle(name='Hadoop', version='1.0')
        b1.save()
        b2 = Bundle(name='Zookeper', version='1.0')
        b2.save()
        b3 = Bundle(name='Hadoop', version='2.0')
        b3.save()

        assert [b1, b3] == list(r.filter())

    @pytest.mark.django_db
    def test_object_filter_error(self):
        r1 = Role(
            name='view',
            display_name='view',
            module_name='rbac.roles',
            class_name='ObjectRole',
            init_params={'app_name': 'cm', 'model': 'qwe'},
        )
        r1.save()
        with pytest.raises(AdwpEx) as e:
            r1.filter()
        assert e.value.error_code == 'ROLE_FILTER_ERROR'

        r2 = Role(
            name='add',
            display_name='add',
            module_name='rbac.roles',
            class_name='ObjectRole',
            init_params={'app_name': 'qwe', 'model': 'qwe'},
        )
        r2.save()
        with pytest.raises(AdwpEx) as e:
            r2.filter()
        assert e.value.error_code == 'ROLE_FILTER_ERROR'

    @pytest.mark.django_db
    def test_object_complex_filter(self):
        r = Role(
            name='view',
            module_name='rbac.roles',
            class_name='ObjectRole',
            init_params={
                'app_name': 'cm',
                'model': 'Action',
                'filter': {
                    'name': 'start',
                    'prototype__type': 'cluster',
                    'prototype__name': 'Kafka',
                    'prototype__bundle__name': 'Hadoop',
                },
            },
        )
        r.save()

        b1 = Bundle(name='Hadoop', version='1.0')
        b1.save()
        p1 = Prototype(bundle=b1, type='cluster', name='Kafka', version='1.0')
        p1.save()
        a1 = Action(prototype=p1, name='start')
        a1.save()
        a2 = Action(prototype=p1, name='stop')
        a2.save()

        assert [a1] == list(r.filter())
