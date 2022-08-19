from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

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


class BaseTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.create_bundles_and_prototypes()
        self.cluster_1 = Cluster.objects.create(name=f'Cluster_1', prototype=self.clp_1)
        self.user_1 = User.objects.create(username='user_1', is_active=True, is_superuser=False)
        self.user_2 = User.objects.create(username='user_2', is_active=True, is_superuser=False)
        self.group_1 = Group.objects.create(name='group_1')
        self.group_2 = Group.objects.create(name='group_2')
        self.create_permissions()

    @staticmethod
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

    def cook_user(self, name):
        return User.objects.create(username=name, is_active=True, is_superuser=False)

    def cook_group(self, name):
        return Group.objects.create(name=name)

    def cook_perm(self, app, model, codename='cm'):
        content, _ = ContentType.objects.get_or_create(app_label=app, model=model)
        perm, _ = Permission.objects.get_or_create(
            codename=f'{codename}_{model}', content_type=content
        )
        return perm

    def create_permissions(self):
        self.add_host_perm = self.cook_perm('add', 'host')
        self.view_cluster_perm = self.cook_perm('view', 'cluster')
        self.view_service_perm = self.cook_perm('view', 'clusterobject')
        self.view_component_perm = self.cook_perm('view', 'servicecomponent')
        self.change_cluster_config_perm = self.cook_perm('change_config_of', 'cluster')
        self.change_service_config_perm = self.cook_perm('change_config_of', 'clusterobject')
        self.change_component_config_perm = self.cook_perm('change_config_of', 'servicecomponent')
        self.change_host_config_perm = self.cook_perm('change_config_of', 'host')
        self.change_provider_config_perm = self.cook_perm('change_config_of', 'hostprovider')

    def create_bundles_and_prototypes(self):
        self.bundle_1 = Bundle.objects.create(name=f'cluster_bundle_1', version='1.0')
        self.bundle_2 = Bundle.objects.create(name=f'cluster_bundle_2', version='1.0')
        self.bundle_3 = Bundle.objects.get_or_create(name='provider_bundle', version='1.0')
        self.clp_1 = Prototype.objects.create(
            bundle=self.bundle_1, type='cluster', name=f'cluster_1'
        )
        self.cp_2 = Prototype.objects.create(
            bundle=self.bundle_2, type='cluster', name=f'cluster_2'
        )
        self.sp_1 = Prototype.objects.create(
            bundle=self.bundle_1, type='service', name=f'service_1'
        )
        self.sp_2 = Prototype.objects.create(
            bundle=self.bundle_1, type='service', name=f'service_2'
        )
        self.cop_11 = Prototype.objects.create(
            bundle=self.bundle_1, type='component', name=f'component_11', parent=self.sp_1
        )
        self.cop_12 = Prototype.objects.create(
            bundle=self.bundle_1, type='component', name=f'component_12', parent=self.sp_1
        )
        self.cop_21 = Prototype.objects.create(
            bundle=self.bundle_1, type='component', name=f'component_21', parent=self.sp_2
        )
        self.cop_22 = Prototype.objects.create(
            bundle=self.bundle_1, type='component', name=f'component_22', parent=self.sp_2
        )

    def create_roles(self):
        self.add_host_model = self.cook_role('add host role', 'ModelRole')
        self.add_host_model.permissions.add(self.add_host_perm)
        self.view_cluster_object = self.cook_role('view cluster', 'ObjectRole')
        self.view_cluster_object.permissions.add(self.view_service_perm)

        model_cluster_role = self.cook_role('view_cluster', 'ModelRole')
        model_cluster_role.permissions.add(self.view_cluster_perm)
        model_service_role = self.cook_role('view_service', 'ModelRole')
        model_service_role.permissions.add(self.view_service_perm)
        model_component_role = self.cook_role('view_component', 'ModelRole')
        model_component_role.permissions.add(self.view_component_perm)
        self.model_view_role = self.cook_role('Model Parent Role', 'ParentRole')
        self.model_view_role.child.add(model_cluster_role, model_service_role, model_component_role)

        cluster_role = self.cook_role('cluster_change_config', 'ObjectRole', ['cluster'])
        cluster_role.permissions.add(self.change_cluster_config_perm)
        service_role = self.cook_role('service_change_config', 'ObjectRole', ['service'])
        service_role.permissions.add(self.change_service_config_perm)
        component_role = self.cook_role('component_change_config', 'ObjectRole', ['component'])
        component_role.permissions.add(self.change_component_config_perm)
        provider_role = self.cook_role('provider_change_config', 'ObjectRole', ['provider'])
        provider_role.permissions.add(self.change_provider_config_perm)
        host_role = self.cook_role('host_change_config', 'ObjectRole', ['host'])
        host_role.permissions.add(self.change_host_config_perm)

    def get_bundle(number):
        bundle, _ = Bundle.objects.get_or_create(name=f'bundle_{number}', version='1.0')
        return bundle

    def get_cluster(bundle, number):
        cp, _ = Prototype.objects.get_or_create(
            bundle=bundle, type='cluster', name=f'cluster_{number}'
        )
        cluster, _ = Cluster.objects.get_or_create(name=f'Cluster {number}', prototype=cp)
        return cluster

    def get_service(cluster, bundle, number):
        sp, _ = Prototype.objects.get_or_create(
            bundle=bundle, type='service', name=f'service_{number}'
        )
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

    def bundle1():
        bundle = get_bundle(1)
        return bundle

    def cluster1():
        bundle = get_bundle(1)
        cluster = get_cluster(bundle, 1)
        return cluster

    def service1():
        bundle = get_bundle(1)
        cluster = get_cluster(bundle, 1)
        service = get_service(cluster, bundle, 1)
        return service

    def service2():
        bundle = get_bundle(1)
        cluster = get_cluster(bundle, 1)
        service = get_service(cluster, bundle, 2)
        return service

    def component11():
        bundle = get_bundle(1)
        cluster = get_cluster(bundle, 1)
        service = get_service(cluster, bundle, 1)
        component = get_component(cluster, service, bundle, 1)
        return component

    def component12():
        bundle = get_bundle(1)
        cluster = get_cluster(bundle, 1)
        service = get_service(cluster, bundle, 1)
        component = get_component(cluster, service, bundle, 2)
        return component

    def component21():
        bundle = get_bundle(1)
        cluster = get_cluster(bundle, 1)
        service = get_service(cluster, bundle, 2)
        component = get_component(cluster, service, bundle, 1)
        return component

    def cluster2():
        bundle = get_bundle(2)
        cluster = get_cluster(bundle, 2)
        return cluster

    def provider():
        p, _ = get_provider()
        return p

    def host1():
        p, bundle = get_provider()
        host = get_host(bundle, p, 1)
        return host

    def host2():
        p, bundle = get_provider()
        host = get_host(bundle, p, 2)
        return host

    def host3():
        p, bundle = get_provider()
        host = get_host(bundle, p, 3)
        return host

    def object_role():
        return cook_role('object role', 'ObjectRole')

    def model_role():
        return cook_role('model role', 'ModelRole')

    def user():
        return cook_user('user')

    def user1():
        return cook_user('user1')

    def group():
        return cook_group('group')

    def group1():
        return cook_group('group1')

    def add_host_perm():
        return cook_perm('cm', 'add', 'host')

    def view_cluster_perm():
        return cook_perm('cm', 'view', 'cluster')

    def object_role_view_perm_cluster():
        cluster_role = cook_role('view_cluster', 'ObjectRole', ['cluster'])
        cluster_role.permissions.add(cook_perm('cm', 'view', 'cluster'))
        role = cook_role('view', 'ParentRole')
        role.child.add(cluster_role)
        return role

    def object_role_custom_perm_cluster_service():
        cluster_role = cook_role('cluster_change_config', 'ObjectRole', ['cluster'])
        cluster_role.permissions.add(cook_perm('cm', 'change_config_of', 'cluster'))
        service_role = cook_role('service_change_config', 'ObjectRole', ['service'])
        service_role.permissions.add(cook_perm('cm', 'change_config_of', 'clusterobject'))
        role = cook_role('change_config', 'ParentRole')
        role.child.add(cluster_role, service_role)
        return role

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

    def object_role_custom_perm_cluster_host():
        cluster_role = cook_role('cluster_change_config', 'ObjectRole', ['cluster'])
        cluster_role.permissions.add(cook_perm('cm', 'change_config_of', 'cluster'))
        host_role = cook_role('host_change_config', 'ObjectRole', ['host'])
        host_role.permissions.add(cook_perm('cm', 'change_config_of', 'host'))
        role = cook_role('change_config', 'ParentRole')
        role.child.add(cluster_role, host_role)
        return role

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

    def object_role_custom_perm_provider_host():
        provider_role = cook_role('provider_change_config', 'ObjectRole', ['provider'])
        provider_role.permissions.add(cook_perm('cm', 'change_config_of', 'hostprovider'))
        host_role = cook_role('host_change_config', 'ObjectRole', ['host'])
        host_role.permissions.add(cook_perm('cm', 'change_config_of', 'host'))
        role = cook_role('change_config', 'ParentRole')
        role.child.add(provider_role, host_role)
        return role

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
