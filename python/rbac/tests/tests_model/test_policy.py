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

import pytest

from django.contrib.contenttypes.models import ContentType
from adwp_base.errors import AdwpEx

from rbac.models import Role, Policy, User, Group, Permission
from rbac.roles import ModelRole
from cm.models import Bundle, Prototype, Action, Cluster, ClusterObject, ServiceComponent
from cm.models import HostProvider, HostComponent
from cm import api


@pytest.mark.django_db
def test_role_class():
    r = Role(module_name='qwe')
    with pytest.raises(AdwpEx) as e:
        r.get_role_obj()
    assert e.value.error_code == 'ROLE_MODULE_ERROR'

    r = Role(module_name='rbac', class_name='qwe')
    with pytest.raises(AdwpEx) as e:
        r.get_role_obj()
    assert e.value.error_code == 'ROLE_CLASS_ERROR'

    r = Role(module_name='rbac.roles', class_name='ModelRole')
    obj = r.get_role_obj()
    assert isinstance(obj, ModelRole)


def cook_user(name):
    return User.objects.create(username=name, is_active=True, is_superuser=False)


def cook_group(name):
    return Group.objects.create(name=name)


def cook_perm(app, codename, model):
    content, _ = ContentType.objects.get_or_create(app_label=app, model=model)
    perm, _ = Permission.objects.get_or_create(codename=f'{codename}_{model}', content_type=content)
    return perm


def cook_role(name, class_name, obj_type=None):
    if obj_type is None:
        obj_type = []
    return Role.objects.create(
        name=name,
        display_name=name,
        module_name='rbac.roles',
        class_name=class_name,
        parametrized_by_type=obj_type,
    )


def clear_perm_cache(user):
    if hasattr(user, '_perm_cache'):
        delattr(user, '_perm_cache')
    if hasattr(user, '_user_perm_cache'):
        delattr(user, '_user_perm_cache')
    if hasattr(user, '_group_perm_cache'):
        delattr(user, '_group_perm_cache')


@pytest.mark.django_db
def test_model_policy():
    user = cook_user('Joe')
    r = cook_role('add', 'ModelRole')
    perm = cook_perm('adcm', 'add', 'host')
    r.permissions.add(perm)

    p = Policy.objects.create(name='MyPolicy', role=r)
    p.user.add(user)

    assert perm not in user.user_permissions.all()
    assert not user.has_perm('adcm.add_host')
    clear_perm_cache(user)

    p.apply()
    assert perm in user.user_permissions.all()
    assert user.has_perm('adcm.add_host')

    clear_perm_cache(user)
    p.apply()
    assert user.has_perm('adcm.add_host')


@pytest.mark.django_db
def test_model_policy4group():
    group = cook_group('Ops')
    user = cook_user('Joe')
    group.user_set.add(user)

    r = cook_role('add', 'ModelRole')
    perm = cook_perm('adcm', 'add', 'host')
    r.permissions.add(perm)

    p = Policy.objects.create(name='MyPolicy', role=r)
    p.group.add(group)

    assert perm not in group.permissions.all()
    assert not user.has_perm('adcm.add_host')
    clear_perm_cache(user)

    p.apply()
    assert perm in group.permissions.all()
    assert user.has_perm('adcm.add_host')

    clear_perm_cache(user)
    p.apply()
    assert user.has_perm('adcm.add_host')


@pytest.mark.django_db
def test_object_policy():
    user = cook_user('Joe')
    r = cook_role('view', 'ObjectRole')
    r.permissions.add(cook_perm('cm', 'view', 'bundle'))

    p = Policy.objects.create(name='MyPolicy', role=r)
    p.user.add(user)

    b1 = Bundle.objects.create(name='ADH', version='1.0')
    b2 = Bundle.objects.create(name='ADH', version='2.0')

    p.add_object(b1)
    assert not user.has_perm('cm.view_bundle', b1)

    p.apply()

    assert user.has_perm('cm.view_bundle', b1)
    assert not user.has_perm('cm.view_bundle', b2)

    p.apply()

    assert user.has_perm('cm.view_bundle', b1)
    assert not user.has_perm('cm.view_bundle', b2)


@pytest.mark.django_db
def test_object_policy_remove_user():
    user = cook_user('Joe')
    r = cook_role('view', 'ObjectRole')
    r.permissions.add(cook_perm('cm', 'view', 'bundle'))

    p = Policy.objects.create(name='MyPolicy', role=r)
    p.user.add(user)

    b1 = Bundle.objects.create(name='ADH', version='1.0')
    b2 = Bundle.objects.create(name='ADH', version='2.0')

    p.add_object(b1)
    assert not user.has_perm('cm.view_bundle', b1)

    p.apply()

    assert user.has_perm('cm.view_bundle', b1)
    assert not user.has_perm('cm.view_bundle', b2)

    p.user.remove(user)
    p.apply()

    assert not user.has_perm('cm.view_bundle', b1)
    assert not user.has_perm('cm.view_bundle', b2)


@pytest.mark.django_db
def test_object_policy4group():
    group = cook_group('Ops')
    user = cook_user('Joe')
    group.user_set.add(user)

    r = cook_role('view', 'ObjectRole')
    r.permissions.add(cook_perm('cm', 'view', 'bundle'))

    p = Policy.objects.create(name='MyPolicy', role=r)
    p.group.add(group)

    b1 = Bundle.objects.create(name='ADH', version='1.0')
    b2 = Bundle.objects.create(name='ADH', version='2.0')

    p.add_object(b1)
    assert not user.has_perm('cm.view_bundle', b1)

    p.apply()

    assert user.has_perm('cm.view_bundle', b1)
    assert not user.has_perm('cm.view_bundle', b2)

    p.apply()

    assert user.has_perm('cm.view_bundle', b1)
    assert not user.has_perm('cm.view_bundle', b2)


def cook_conf_role():
    r_cluster = cook_role('cluster_conf', 'ObjectRole', ['cluster'])
    r_cluster.permissions.add(cook_perm('cm', 'edit_conf', 'cluster'))

    r_service = cook_role('service_conf', 'ObjectRole', ['service'])
    r_service.permissions.add(cook_perm('cm', 'edit_conf', 'clusterobject'))

    r_comp = cook_role('component_conf', 'ObjectRole', ['component'])
    r_comp.permissions.add(cook_perm('cm', 'edit_conf', 'servicecomponent'))

    r_provider = cook_role('provider_conf', 'ObjectRole', ['provider'])
    r_provider.permissions.add(cook_perm('cm', 'edit_conf', 'hostprovider'))

    r_host = cook_role('host_conf', 'ObjectRole', ['host'])
    r_host.permissions.add(cook_perm('cm', 'edit_conf', 'host'))

    r = cook_role('all_conf', 'ParentRole')
    r.child.add(r_cluster, r_service, r_comp, r_provider, r_host)

    return r


def cook_cluster1():
    b = Bundle.obj.create(name='Adh', version='1.0')
    cp = Prototype.obj.create(bundle=b, type='cluster', name='ADH')
    cluster = Cluster.obj.create(name='Yukon', prototype=cp)

    sp1 = Prototype.obj.create(bundle=b, type='service', name='Hadoop')
    service1 = ClusterObject.obj.create(cluster=cluster, prototype=sp1)
    cp11 = Prototype.obj.create(bundle=b, type='component', name='server')
    comp11 = ServiceComponent.obj.create(cluster=cluster, service=service1, prototype=cp11)
    cp12 = Prototype.obj.create(bundle=b, type='component', name='node')
    comp12 = ServiceComponent.obj.create(cluster=cluster, service=service1, prototype=cp12)

    sp2 = Prototype.obj.create(bundle=b, type='service', name='Kafka')
    service2 = ClusterObject.obj.create(cluster=cluster, prototype=sp2)
    cp21 = Prototype.obj.create(bundle=b, type='component', name='node2')
    comp21 = ServiceComponent.obj.create(cluster=cluster, service=service2, prototype=cp21)

    return (cluster, service1, service2, comp11, comp12, comp21, b)


def cook_hosts():
    b = Bundle.obj.create(name='ssh', version='1.0')
    hpp = Prototype.obj.create(bundle=b, type='provider', name='Cloud')
    provider = HostProvider.obj.create(name='Fort', prototype=hpp)
    hp = Prototype.obj.create(bundle=b, type='host', name='Simple')

    host1 = api.add_host(hp, provider, 'host1.net')
    host2 = api.add_host(hp, provider, 'host2.net')
    host3 = api.add_host(hp, provider, 'host3.net')

    return (provider, host1, host2, host3)


@pytest.mark.django_db
def test_parent_policy4cluster():
    user = cook_user('Joe')
    cluster, service1, service2, comp11, comp12, comp21, _ = cook_cluster1()

    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)
    p.add_object(cluster)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert not user.has_perm('cm.edit_conf_clusterobject', service2)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp11)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp12)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp21)

    p.apply()

    assert user.has_perm('cm.edit_conf_cluster', cluster)
    assert user.has_perm('cm.edit_conf_clusterobject', service1)
    assert user.has_perm('cm.edit_conf_clusterobject', service2)
    assert user.has_perm('cm.edit_conf_servicecomponent', comp11)
    assert user.has_perm('cm.edit_conf_servicecomponent', comp12)
    assert user.has_perm('cm.edit_conf_servicecomponent', comp21)


@pytest.mark.django_db
def test_parent_policy4service():
    user = cook_user('Joe')
    cluster, service1, service2, comp11, comp12, comp21, _ = cook_cluster1()
    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)

    p.add_object(service1)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert not user.has_perm('cm.edit_conf_clusterobject', service2)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp11)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp12)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp21)

    p.apply()

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert user.has_perm('cm.edit_conf_clusterobject', service1)
    assert not user.has_perm('cm.edit_conf_clusterobject', service2)
    assert user.has_perm('cm.edit_conf_servicecomponent', comp11)
    assert user.has_perm('cm.edit_conf_servicecomponent', comp12)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp21)


@pytest.mark.django_db
def test_parent_policy4service2():
    user = cook_user('Joe')
    cluster, service1, service2, comp11, comp12, comp21, _ = cook_cluster1()
    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)

    p.add_object(service2)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert not user.has_perm('cm.edit_conf_clusterobject', service2)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp11)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp12)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp21)

    p.apply()

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert user.has_perm('cm.edit_conf_clusterobject', service2)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp11)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp12)
    assert user.has_perm('cm.edit_conf_servicecomponent', comp21)


@pytest.mark.django_db
def test_parent_policy4component():
    user = cook_user('Joe')
    cluster, service1, service2, comp11, comp12, comp21, _ = cook_cluster1()
    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)

    p.add_object(comp12)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert not user.has_perm('cm.edit_conf_clusterobject', service2)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp11)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp12)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp21)

    p.apply()

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert not user.has_perm('cm.edit_conf_clusterobject', service2)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp11)
    assert user.has_perm('cm.edit_conf_servicecomponent', comp12)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp21)


@pytest.mark.django_db
def test_parent_policy4host_in_cluster():
    user = cook_user('Joe')
    cluster, _, _, _, _, _, _ = cook_cluster1()
    _, host1, host2, host3 = cook_hosts()
    api.add_host_to_cluster(cluster, host1)
    api.add_host_to_cluster(cluster, host2)

    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)
    p.add_object(cluster)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_host', host1)
    assert not user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)

    p.apply()

    assert user.has_perm('cm.edit_conf_cluster', cluster)
    assert user.has_perm('cm.edit_conf_host', host1)
    assert user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)


@pytest.mark.django_db
def test_parent_policy4host_in_service():
    user = cook_user('Joe')
    cluster, service1, service2, comp11, comp12, comp21, _ = cook_cluster1()
    _, host1, host2, host3 = cook_hosts()
    api.add_host_to_cluster(cluster, host1)
    api.add_host_to_cluster(cluster, host2)
    api.add_host_to_cluster(cluster, host3)
    api.add_hc(
        cluster,
        [
            {"service_id": service1.id, "component_id": comp11.id, "host_id": host1.id},
            {"service_id": service1.id, "component_id": comp12.id, "host_id": host2.id},
            {"service_id": service2.id, "component_id": comp21.id, "host_id": host3.id},
        ],
    )

    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)
    p.add_object(service1)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert not user.has_perm('cm.edit_conf_host', host1)
    assert not user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)

    p.apply()

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert user.has_perm('cm.edit_conf_clusterobject', service1)
    assert user.has_perm('cm.edit_conf_host', host1)
    assert user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)


@pytest.mark.django_db
def test_parent_policy4host_in_component():
    user = cook_user('Joe')
    cluster, service1, service2, comp11, _, comp21, _ = cook_cluster1()
    _, host1, host2, host3 = cook_hosts()
    api.add_host_to_cluster(cluster, host1)
    api.add_host_to_cluster(cluster, host2)
    api.add_host_to_cluster(cluster, host3)
    HostComponent.obj.create(cluster=cluster, service=service2, component=comp21, host=host1)
    HostComponent.obj.create(cluster=cluster, service=service2, component=comp21, host=host2)
    HostComponent.obj.create(cluster=cluster, service=service1, component=comp11, host=host3)

    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)
    p.add_object(comp21)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert not user.has_perm('cm.edit_conf_servicecomponent', comp21)
    assert not user.has_perm('cm.edit_conf_host', host1)
    assert not user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)

    p.apply()

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert user.has_perm('cm.edit_conf_servicecomponent', comp21)
    assert user.has_perm('cm.edit_conf_host', host1)
    assert user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)


@pytest.mark.django_db
def test_parent_policy4provider():
    user = cook_user('Joe')
    provider, host1, host2, host3 = cook_hosts()

    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)
    p.add_object(provider)

    assert not user.has_perm('cm.edit_conf_hostprovider', provider)
    assert not user.has_perm('cm.edit_conf_host', host1)
    assert not user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)

    p.apply()

    assert user.has_perm('cm.edit_conf_hostprovider', provider)
    assert user.has_perm('cm.edit_conf_host', host1)
    assert user.has_perm('cm.edit_conf_host', host2)
    assert user.has_perm('cm.edit_conf_host', host3)


@pytest.mark.django_db
def test_simple_parent_policy():
    user = cook_user('Joe')

    cluster = cook_role('change_cluster', 'ModelRole')
    cluster.permissions.add(cook_perm('cm', 'change', 'cluster'))

    service = cook_role('change_service', 'ModelRole')
    service.permissions.add(cook_perm('cm', 'change', 'clusterobject'))

    comp = cook_role('change_component', 'ModelRole')
    comp.permissions.add(cook_perm('cm', 'change', 'servicecomponent'))

    r = cook_role('all', 'ParentRole')
    r.child.add(cluster, service, comp)

    p = Policy.objects.create(role=r)
    p.user.add(user)

    assert not user.has_perm('cm.change_cluster')
    assert not user.has_perm('cm.change_clusterobject')
    assert not user.has_perm('cm.change_servicecomponent')

    clear_perm_cache(user)
    p.apply()

    assert user.has_perm('cm.change_cluster')
    assert user.has_perm('cm.change_clusterobject')
    assert user.has_perm('cm.change_servicecomponent')


@pytest.mark.django_db
def test_empty_parent_policy():
    user = cook_user('Joe')
    _, _, service2, _, _, _, _ = cook_cluster1()

    r = cook_role('all', 'ParentRole', ['service'])
    p = Policy.objects.create(role=r)
    p.user.add(user)
    p.add_object(service2)

    p.apply()


@pytest.mark.django_db
def test_add_service():
    user = cook_user('Joe')
    cluster, service1, service2, _, _, _, b = cook_cluster1()
    sp3 = Prototype.obj.create(bundle=b, type='service', name='Hive')

    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)
    p.add_object(cluster)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_clusterobject', service1)
    assert not user.has_perm('cm.edit_conf_clusterobject', service2)

    p.apply()

    assert user.has_perm('cm.edit_conf_cluster', cluster)
    assert user.has_perm('cm.edit_conf_clusterobject', service1)
    assert user.has_perm('cm.edit_conf_clusterobject', service2)

    service3 = api.add_service_to_cluster(cluster, sp3)
    assert user.has_perm('cm.edit_conf_clusterobject', service3)


@pytest.mark.django_db
def test_add_host():
    user = cook_user('Joe')
    cluster, service1, _, comp11, comp12, _, _ = cook_cluster1()
    _, host1, host2, host3 = cook_hosts()
    api.add_host_to_cluster(cluster, host1)
    api.add_host_to_cluster(cluster, host2)
    HostComponent.obj.create(cluster=cluster, service=service1, component=comp11, host=host1)
    HostComponent.obj.create(cluster=cluster, service=service1, component=comp12, host=host2)

    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)
    p.add_object(cluster)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_host', host1)
    assert not user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)

    p.apply()

    assert user.has_perm('cm.edit_conf_cluster', cluster)
    assert user.has_perm('cm.edit_conf_host', host1)
    assert user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)

    api.add_host_to_cluster(cluster, host3)

    assert user.has_perm('cm.edit_conf_host', host3)


@pytest.mark.django_db
def test_add_hc():
    user = cook_user('Joe')
    cluster, service1, _, comp11, comp12, _, _ = cook_cluster1()
    _, host1, host2, host3 = cook_hosts()
    api.add_host_to_cluster(cluster, host1)
    HostComponent.obj.create(cluster=cluster, service=service1, component=comp11, host=host1)

    p = Policy.objects.create(role=cook_conf_role())
    p.user.add(user)
    p.add_object(service1)

    assert not user.has_perm('cm.edit_conf_cluster', cluster)
    assert not user.has_perm('cm.edit_conf_host', host1)
    assert not user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)

    p.apply()

    assert user.has_perm('cm.edit_conf_clusterobject', service1)
    assert user.has_perm('cm.edit_conf_host', host1)
    assert not user.has_perm('cm.edit_conf_host', host2)
    assert not user.has_perm('cm.edit_conf_host', host3)

    api.add_host_to_cluster(cluster, host2)
    api.add_hc(
        cluster,
        [
            {"service_id": service1.id, "component_id": comp11.id, "host_id": host1.id},
            {"service_id": service1.id, "component_id": comp12.id, "host_id": host2.id},
        ],
    )

    assert user.has_perm('cm.edit_conf_host', host2)


@pytest.mark.django_db
def test_object_filter():
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
def test_object_filter_error():
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
def test_object_complex_filter():
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
