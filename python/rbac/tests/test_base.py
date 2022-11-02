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

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from adcm.tests.base import BaseTestCase
from cm.models import Bundle, Prototype
from rbac.models import Role


def cook_perm(codename, model, app="cm"):
    content, _ = ContentType.objects.get_or_create(app_label=app, model=model)
    perm, _ = Permission.objects.get_or_create(codename=f"{codename}_{model}", content_type=content)

    return perm


def cook_role(name, class_name, obj_type=None):
    if obj_type is None:
        obj_type = []

    return Role.objects.create(
        name=name,
        display_name=name,
        module_name="rbac.roles",
        class_name=class_name,
        parametrized_by_type=obj_type,
    )


class RBACBaseTestCase(BaseTestCase):  # pylint: disable=too-many-instance-attributes
    def setUp(self) -> None:
        self.create_bundles_and_prototypes()
        self.create_permissions()

    def create_bundles_and_prototypes(self):
        self.bundle_1 = Bundle.objects.create(name="cluster_bundle", version="1.0")
        self.clp = Prototype.objects.create(
            bundle=self.bundle_1,
            type="cluster",
            name="sample_cluster",
            version="1.0",
            display_name="Sample Cluster",
            allow_maintenance_mode=True,
        )
        self.sp_1 = Prototype.objects.create(
            bundle=self.bundle_1,
            type="service",
            name="service_1",
            version="1.0",
            display_name="Service 1",
            allow_maintenance_mode=True,
        )

        self.sp_2 = Prototype.objects.create(
            bundle=self.bundle_1,
            type="service",
            name="service_2",
            version="1.0",
            display_name="Service 2",
        )

        self.cop_11 = Prototype.objects.create(
            bundle=self.bundle_1,
            type="component",
            name="component_1",
            version="1.0",
            display_name="Component 1 from Service 1",
            parent=self.sp_1,
            allow_maintenance_mode=True,
        )
        self.cop_12 = Prototype.objects.create(
            bundle=self.bundle_1,
            type="component",
            name="component_2",
            version="1.0",
            display_name="Component 2 from Service 1",
            parent=self.sp_1,
        )
        self.cop_21 = Prototype.objects.create(
            bundle=self.bundle_1,
            type="component",
            name="component_1",
            version="1.0",
            display_name="Component 1 from Service 2",
            parent=self.sp_2,
        )
        self.cop_22 = Prototype.objects.create(
            bundle=self.bundle_1,
            type="component",
            name="component_2",
            version="1.0",
            display_name="Component 2 from Service 2",
            parent=self.sp_2,
        )
        self.bundle_2 = Bundle.objects.create(name="provider_bundle", version="1.0")
        self.pp = Prototype.objects.create(
            bundle=self.bundle_2, type="provider", name="provider", allow_maintenance_mode=True
        )
        self.hp = Prototype.objects.create(bundle=self.bundle_2, type="host", name="host", allow_maintenance_mode=True)

    def create_permissions(self):
        self.add_host_perm = cook_perm("add", "host")
        self.view_cluster_perm = cook_perm("view", "cluster")
        self.view_service_perm = cook_perm("view", "clusterobject")
        self.view_component_perm = cook_perm("view", "servicecomponent")
        self.change_cluster_config_perm = cook_perm("change_config_of", "cluster")
        self.change_service_config_perm = cook_perm("change_config_of", "clusterobject")
        self.change_component_config_perm = cook_perm("change_config_of", "servicecomponent")
        self.change_host_config_perm = cook_perm("change_config_of", "host")
        self.change_provider_config_perm = cook_perm("change_config_of", "hostprovider")

    def object_role(self):
        object_role = cook_role("object role", "ObjectRole")
        object_role.permissions.add(self.view_cluster_perm)

        return object_role

    def model_role(self):
        model_role = cook_role("model role", "ModelRole")
        model_role.permissions.add(self.add_host_perm)

        return model_role

    def object_role_view_perm_cluster(self):
        cluster_role = cook_role("view_cluster", "ObjectRole", ["cluster"])
        cluster_role.permissions.add(self.view_cluster_perm)
        role = cook_role("view", "ParentRole")
        role.child.add(cluster_role)

        return role

    def object_role_custom_perm_cluster_service(self):
        cluster_role = cook_role("cluster_change_config", "ObjectRole", ["cluster"])
        cluster_role.permissions.add(self.change_cluster_config_perm)
        service_role = cook_role("service_change_config", "ObjectRole", ["service"])
        service_role.permissions.add(self.change_service_config_perm)
        role = cook_role("change_config", "ParentRole")
        role.child.add(cluster_role, service_role)

        return role

    def object_role_custom_perm_cluster_service_component(self):
        cluster_role = cook_role("cluster_change_config", "ObjectRole", ["cluster"])
        cluster_role.permissions.add(self.change_cluster_config_perm)
        service_role = cook_role("service_change_config", "ObjectRole", ["service"])
        service_role.permissions.add(self.change_service_config_perm)
        component_role = cook_role("component_change_config", "ObjectRole", ["component"])
        component_role.permissions.add(self.change_component_config_perm)
        role = cook_role("change_config", "ParentRole")
        role.child.add(cluster_role, service_role, component_role)

        return role

    def object_role_custom_perm_service_component_host(self):
        service_role = cook_role("service_change_config", "ObjectRole", ["service"])
        service_role.permissions.add(self.change_service_config_perm)
        component_role = cook_role("component_change_config", "ObjectRole", ["component"])
        component_role.permissions.add(self.change_component_config_perm)
        host_role = cook_role("host_change_config", "ObjectRole", ["host"])
        host_role.permissions.add(self.change_host_config_perm)
        role = cook_role("change_config", "ParentRole")
        role.child.add(service_role, component_role, host_role)

        return role

    def object_role_custom_perm_cluster_host(self):
        cluster_role = cook_role("cluster_change_config", "ObjectRole", ["cluster"])
        cluster_role.permissions.add(self.change_cluster_config_perm)
        host_role = cook_role("host_change_config", "ObjectRole", ["host"])
        host_role.permissions.add(self.change_host_config_perm)
        role = cook_role("change_config", "ParentRole")
        role.child.add(cluster_role, host_role)

        return role

    def object_role_custom_perm_cluster_service_component_host(self):
        cluster_role = cook_role("cluster_change_config", "ObjectRole", ["cluster"])
        cluster_role.permissions.add(self.change_cluster_config_perm)
        service_role = cook_role("service_change_config", "ObjectRole", ["service"])
        service_role.permissions.add(self.change_service_config_perm)
        component_role = cook_role("component_change_config", "ObjectRole", ["component"])
        component_role.permissions.add(self.change_component_config_perm)
        host_role = cook_role("host_change_config", "ObjectRole", ["host"])
        host_role.permissions.add(self.change_host_config_perm)
        role = cook_role("change_config", "ParentRole")
        role.child.add(cluster_role, service_role, component_role, host_role)

        return role

    def object_role_custom_perm_provider_host(self):
        provider_role = cook_role("provider_change_config", "ObjectRole", ["provider"])
        provider_role.permissions.add(self.change_provider_config_perm)
        host_role = cook_role("host_change_config", "ObjectRole", ["host"])
        host_role.permissions.add(self.change_host_config_perm)
        role = cook_role("change_config", "ParentRole")
        role.child.add(provider_role, host_role)

        return role

    def model_role_view_cluster_service_component_perm(self):
        cluster_role = cook_role("view_cluster", "ModelRole")
        cluster_role.permissions.add(self.view_cluster_perm)
        service_role = cook_role("view_service", "ModelRole")
        service_role.permissions.add(self.view_service_perm)
        component_role = cook_role("view_component", "ModelRole")
        component_role.permissions.add(self.view_component_perm)
        role = cook_role("view_objects", "ParentRole")
        role.child.add(cluster_role, service_role, component_role)

        return role
