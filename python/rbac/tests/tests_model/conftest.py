import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from cm.models import (
    Bundle,
    Prototype,
    Cluster,
    ClusterObject,
    ServiceComponent,
    HostProvider,
    Host,
)
from rbac.models import Role, User, Group


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


def cook_user(name):
    return User.objects.create(username=name, is_active=True, is_superuser=False)


def cook_group(name):
    return Group.objects.create(name=name)


def cook_perm(app, codename, model):
    content, _ = ContentType.objects.get_or_create(app_label=app, model=model)
    perm, _ = Permission.objects.get_or_create(codename=f'{codename}_{model}', content_type=content)
    return perm


def get_bundle(number):
    bundle, _ = Bundle.objects.get_or_create(name=f'bundle_{number}', version='1.0')
    return bundle


def get_cluster(bundle, number):
    cp, _ = Prototype.objects.get_or_create(bundle=bundle, type='cluster', name=f'cluster_{number}')
    cluster, _ = Cluster.objects.get_or_create(name=f'Cluster {number}', prototype=cp)
    return cluster


def get_service(cluster, bundle, number):
    sp, _ = Prototype.objects.get_or_create(bundle=bundle, type='service', name=f'service_{number}')
    service, _ = ClusterObject.objects.get_or_create(cluster=cluster, prototype=sp)
    return service


def get_component(cluster, service, bundle, number):
    cp, _ = Prototype.objects.get_or_create(
        bundle=bundle, type='component', name=f'component_{number}', parent=service.prototype
    )
    component, _ = ServiceComponent.objects.get_or_create(
        cluster=cluster, service=service, prototype=cp
    )
    return component


def get_provider():
    bundle, _ = Bundle.objects.get_or_create(name='provider', version='1.0')
    pp, _ = Prototype.objects.get_or_create(bundle=bundle, type='provider', name='provider')
    p, _ = HostProvider.objects.get_or_create(name='provider', prototype=pp)
    return p, bundle


def get_host(b, p, number):
    hp, _ = Prototype.objects.get_or_create(bundle=b, type='host', name='host')
    host, _ = Host.objects.get_or_create(prototype=hp, provider=p, fqdn=f'host_{number}')
    return host


@pytest.fixture()
def bundle1():
    bundle = get_bundle(1)
    return bundle


@pytest.fixture()
def cluster1():
    bundle = get_bundle(1)
    cluster = get_cluster(bundle, 1)
    return cluster


@pytest.fixture()
def service1():
    bundle = get_bundle(1)
    cluster = get_cluster(bundle, 1)
    service = get_service(cluster, bundle, 1)
    return service


@pytest.fixture()
def service2():
    bundle = get_bundle(1)
    cluster = get_cluster(bundle, 1)
    service = get_service(cluster, bundle, 2)
    return service


@pytest.fixture()
def component11():
    bundle = get_bundle(1)
    cluster = get_cluster(bundle, 1)
    service = get_service(cluster, bundle, 1)
    component = get_component(cluster, service, bundle, 1)
    return component


@pytest.fixture()
def component12():
    bundle = get_bundle(1)
    cluster = get_cluster(bundle, 1)
    service = get_service(cluster, bundle, 1)
    component = get_component(cluster, service, bundle, 2)
    return component


@pytest.fixture()
def component21():
    bundle = get_bundle(1)
    cluster = get_cluster(bundle, 1)
    service = get_service(cluster, bundle, 2)
    component = get_component(cluster, service, bundle, 1)
    return component


@pytest.fixture()
def cluster2():
    bundle = get_bundle(2)
    cluster = get_cluster(bundle, 2)
    return cluster


@pytest.fixture()
def provider():
    p, _ = get_provider()
    return p


@pytest.fixture()
def host1():
    p, bundle = get_provider()
    host = get_host(bundle, p, 1)
    return host


@pytest.fixture()
def host2():
    p, bundle = get_provider()
    host = get_host(bundle, p, 2)
    return host


@pytest.fixture()
def host3():
    p, bundle = get_provider()
    host = get_host(bundle, p, 3)
    return host


@pytest.fixture
def object_role():
    return cook_role('object role', 'ObjectRole')


@pytest.fixture()
def model_role():
    return cook_role('model role', 'ModelRole')


@pytest.fixture()
def user():
    return cook_user('user')


@pytest.fixture()
def user1():
    return cook_user('user1')


@pytest.fixture()
def group():
    return cook_group('group')


@pytest.fixture()
def group1():
    return cook_group('group1')


@pytest.fixture()
def add_host_perm():
    return cook_perm('cm', 'add', 'host')


@pytest.fixture()
def view_cluster_perm():
    return cook_perm('cm', 'view', 'cluster')


@pytest.fixture()
def object_role_view_perm_cluster():
    cluster_role = cook_role('view_cluster', 'ObjectRole', ['cluster'])
    cluster_role.permissions.add(cook_perm('cm', 'view', 'cluster'))
    role = cook_role('view', 'ParentRole')
    role.child.add(cluster_role)
    return role


@pytest.fixture()
def object_role_custom_perm_cluster_service():
    cluster_role = cook_role('cluster_change_config', 'ObjectRole', ['cluster'])
    cluster_role.permissions.add(cook_perm('cm', 'change_config_of', 'cluster'))
    service_role = cook_role('service_change_config', 'ObjectRole', ['service'])
    service_role.permissions.add(cook_perm('cm', 'change_config_of', 'clusterobject'))
    role = cook_role('change_config', 'ParentRole')
    role.child.add(cluster_role, service_role)
    return role


@pytest.fixture()
def object_role_custom_perm_cluster_service_component():
    cluster_role = cook_role('cluster_change_config', 'ObjectRole', ['cluster'])
    cluster_role.permissions.add(cook_perm('cm', 'change_config_of', 'cluster'))
    service_role = cook_role('service_change_config', 'ObjectRole', ['service'])
    service_role.permissions.add(cook_perm('cm', 'change_config_of', 'clusterobject'))
    component_role = cook_role('component_change_config', 'ObjectRole', ['component'])
    component_role.permissions.add(cook_perm('cm', 'change_config_of', 'servicecomponent'))
    role = cook_role('change_config', 'ParentRole')
    role.child.add(cluster_role, service_role, component_role)
    return role


@pytest.fixture()
def object_role_custom_perm_service_component_host():
    service_role = cook_role('service_change_config', 'ObjectRole', ['service'])
    service_role.permissions.add(cook_perm('cm', 'change_config_of', 'clusterobject'))
    component_role = cook_role('component_change_config', 'ObjectRole', ['component'])
    component_role.permissions.add(cook_perm('cm', 'change_config_of', 'servicecomponent'))
    host_role = cook_role('host_change_config', 'ObjectRole', ['host'])
    host_role.permissions.add(cook_perm('cm', 'change_config_of', 'host'))
    role = cook_role('change_config', 'ParentRole')
    role.child.add(service_role, component_role, host_role)
    return role


@pytest.fixture()
def object_role_custom_perm_cluster_host():
    cluster_role = cook_role('cluster_change_config', 'ObjectRole', ['cluster'])
    cluster_role.permissions.add(cook_perm('cm', 'change_config_of', 'cluster'))
    host_role = cook_role('host_change_config', 'ObjectRole', ['host'])
    host_role.permissions.add(cook_perm('cm', 'change_config_of', 'host'))
    role = cook_role('change_config', 'ParentRole')
    role.child.add(cluster_role, host_role)
    return role


@pytest.fixture()
def object_role_custom_perm_cluster_service_component_host():
    cluster_role = cook_role('cluster_change_config', 'ObjectRole', ['cluster'])
    cluster_role.permissions.add(cook_perm('cm', 'change_config_of', 'cluster'))
    service_role = cook_role('service_change_config', 'ObjectRole', ['service'])
    service_role.permissions.add(cook_perm('cm', 'change_config_of', 'clusterobject'))
    component_role = cook_role('component_change_config', 'ObjectRole', ['component'])
    component_role.permissions.add(cook_perm('cm', 'change_config_of', 'servicecomponent'))
    host_role = cook_role('host_change_config', 'ObjectRole', ['host'])
    host_role.permissions.add(cook_perm('cm', 'change_config_of', 'host'))
    role = cook_role('change_config', 'ParentRole')
    role.child.add(cluster_role, service_role, component_role, host_role)
    return role


@pytest.fixture()
def object_role_custom_perm_provider_host():
    provider_role = cook_role('provider_change_config', 'ObjectRole', ['provider'])
    provider_role.permissions.add(cook_perm('cm', 'change_config_of', 'hostprovider'))
    host_role = cook_role('host_change_config', 'ObjectRole', ['host'])
    host_role.permissions.add(cook_perm('cm', 'change_config_of', 'host'))
    role = cook_role('change_config', 'ParentRole')
    role.child.add(provider_role, host_role)
    return role


@pytest.fixture()
def model_role_view_cluster_service_component_perm():
    cluster_role = cook_role('view_cluster', 'ModelRole')
    cluster_role.permissions.add(cook_perm('cm', 'view', 'cluster'))
    service_role = cook_role('view_service', 'ModelRole')
    service_role.permissions.add(cook_perm('cm', 'view', 'clusterobject'))
    component_role = cook_role('view_component', 'ModelRole')
    component_role.permissions.add(cook_perm('cm', 'view', 'servicecomponent'))
    role = cook_role('view_objects', 'ParentRole')
    role.child.add(cluster_role, service_role, component_role)
    return role
