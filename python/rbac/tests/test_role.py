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

import json

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from api.utils import PermissionDenied, check_custom_perm
from cm.api import add_host_to_cluster
from cm.errors import AdcmEx
from cm.models import (
    Action,
    ActionType,
    Bundle,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    MaintenanceMode,
    ProductCategory,
    Prototype,
    ServiceComponent,
)
from init_db import init as init_adcm
from rbac.models import Role, RoleTypes, User
from rbac.roles import ModelRole
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rbac.tests.test_base import RBACBaseTestCase
from rbac.upgrade.role import init_roles, prepare_action_roles


class RoleModelTest(BaseTestCase):
    def test_role_class(self):
        role = Role(module_name="qwe")
        with self.assertRaises(AdcmEx) as context:
            role.get_role_obj()

        self.assertEqual(context.exception.code, "ROLE_MODULE_ERROR")

        role = Role(module_name="rbac", class_name="qwe")
        with self.assertRaises(AdcmEx) as context:
            role.get_role_obj()

        self.assertEqual(context.exception.code, "ROLE_CLASS_ERROR")

        role = Role(module_name="rbac.roles", class_name="ModelRole")
        obj = role.get_role_obj()

        self.assertTrue(isinstance(obj, ModelRole))

    def test_default(self):
        role = Role.objects.create()

        self.assertEqual(role.name, "")
        self.assertEqual(role.description, "")
        self.assertFalse(role.child.exists())
        self.assertFalse(role.permissions.exists())
        self.assertEqual(role.module_name, "")
        self.assertEqual(role.class_name, "")
        self.assertEqual(role.init_params, {})
        self.assertTrue(role.built_in)
        self.assertEqual(role.parametrized_by_type, [])

    def test_object_filter(self):
        role = Role(
            name="view",
            module_name="rbac.roles",
            class_name="ObjectRole",
            init_params={
                "app_name": "cm",
                "model": "Bundle",
                "filter": {"name": "Hadoop"},
            },
        )
        role.save()

        bundle_1 = Bundle(name="Hadoop", version="1.0")
        bundle_1.save()

        bundle_2 = Bundle(name="Zookeper", version="1.0")
        bundle_2.save()

        bundle_3 = Bundle(name="Hadoop", version="2.0")
        bundle_3.save()

        self.assertEqual([bundle_1, bundle_3], list(role.filter()))

    def test_object_filter_error(self):
        role_1 = Role(
            name="view",
            display_name="view",
            module_name="rbac.roles",
            class_name="ObjectRole",
            init_params={"app_name": "cm", "model": "qwe"},
        )
        role_1.save()
        with self.assertRaises(AdcmEx) as e:
            role_1.filter()

        self.assertEqual(e.exception.code, "ROLE_FILTER_ERROR")

        role_2 = Role(
            name="add",
            display_name="add",
            module_name="rbac.roles",
            class_name="ObjectRole",
            init_params={"app_name": "qwe", "model": "qwe"},
        )
        role_2.save()
        with self.assertRaises(AdcmEx) as e:
            role_1.filter()

        self.assertEqual(e.exception.code, "ROLE_FILTER_ERROR")

    def test_object_complex_filter(self):
        role = Role(
            name="view",
            module_name="rbac.roles",
            class_name="ObjectRole",
            init_params={
                "app_name": "cm",
                "model": "Action",
                "filter": {
                    "name": "start",
                    "prototype__type": "cluster",
                    "prototype__name": "Kafka",
                    "prototype__bundle__name": "Hadoop",
                },
            },
        )
        role.save()

        bundle_1 = Bundle(name="Hadoop", version="1.0")
        bundle_1.save()

        cluster_prototype = Prototype(bundle=bundle_1, type="cluster", name="Kafka", version="1.0")
        cluster_prototype.save()

        action_1 = Action(prototype=cluster_prototype, name="start")
        action_1.save()

        action_2 = Action(prototype=cluster_prototype, name="stop")
        action_2.save()

        self.assertEqual([action_1], list(role.filter()))


class RoleFunctionalTestRBAC(RBACBaseTestCase):
    longMessage = False

    def setUp(self):
        super().setUp()

        init_adcm()
        init_roles()

        category = ProductCategory.objects.create(
            value="Sample Cluster",
            visible=True,
        )
        Bundle.objects.filter(id=self.bundle_1.id).update(
            name="sample_bundle",
            version="1.0",
            hash="47b820a6d66a90b02b42017269904ab2c954bceb",
            edition="community",
            category=category,
        )
        self.bundle_1.refresh_from_db()

        self.cluster_action = Action.objects.create(
            name="cluster_action",
            type=ActionType.JOB,
            script="./action.yaml",
            script_type="ansible",
            state_available="any",
            prototype=self.clp,
            display_name="Cluster Action",
        )
        self.service1_action = Action.objects.create(
            name="service_1_action",
            type=ActionType.JOB,
            script="./action.yaml",
            script_type="ansible",
            state_available="any",
            prototype=self.sp_1,
            display_name="Service 1 Action",
        )
        self.component11_action = Action.objects.create(
            name="component_1_1_action",
            type=ActionType.JOB,
            script="./action.yaml",
            script_type="ansible",
            state_available="any",
            prototype=self.cop_11,
            display_name="Component 1 from Service 1 Action",
        )
        self.component21_action = Action.objects.create(
            name="component_2_1_action",
            type=ActionType.JOB,
            script="./action.yaml",
            script_type="ansible",
            state_available="any",
            prototype=self.cop_12,
            display_name="Component 2 from Service 1 Action",
        )
        self.service2_action = Action.objects.create(
            name="service_2_action",
            type=ActionType.JOB,
            script="./action.yaml",
            script_type="ansible",
            state_available="any",
            prototype=self.sp_2,
            display_name="Service 2 Action",
        )
        self.component12_action = Action.objects.create(
            name="component_1_2_action",
            type=ActionType.JOB,
            script="./action.yaml",
            script_type="ansible",
            state_available="any",
            prototype=self.cop_21,
            display_name="Component 1 from Service 2 Action",
        )
        self.component22_action = Action.objects.create(
            name="component_2_2_action",
            type=ActionType.JOB,
            script="./action.yaml",
            script_type="ansible",
            state_available="any",
            prototype=self.cop_22,
            display_name="Component 2 from Service 2 Action",
        )

    def make_roles_list(self):
        roles = [
            # hidden action roles
            {
                "name": "sample_bundle_1.0_community_cluster_Sample Cluster_cluster_action",
                "display_name": "sample_bundle_1.0_community_cluster_Sample Cluster_cluster_action",
                "bundle": self.bundle_1,
                "type": RoleTypes.HIDDEN,
                "module_name": "rbac.roles",
                "class_name": "ActionRole",
                "init_params": {
                    "action_id": self.cluster_action.id,
                    "app_name": "cm",
                    "model": "Cluster",
                    "filter": {
                        "prototype__name": "sample_cluster",
                        "prototype__type": "cluster",
                        "prototype__bundle_id": self.bundle_1.id,
                    },
                },
                "parametrized_by_type": ["cluster"],
            },
            {
                "name": "sample_bundle_1.0_community_service_Service 1_service_1_action",
                "display_name": "sample_bundle_1.0_community_service_Service 1_service_1_action",
                "bundle": self.bundle_1,
                "type": RoleTypes.HIDDEN,
                "module_name": "rbac.roles",
                "class_name": "ActionRole",
                "init_params": {
                    "action_id": self.service1_action.id,
                    "app_name": "cm",
                    "model": "ClusterObject",
                    "filter": {
                        "prototype__name": "service_1",
                        "prototype__type": "service",
                        "prototype__bundle_id": self.bundle_1.id,
                    },
                },
                "parametrized_by_type": ["service"],
            },
            {
                "name": (
                    "sample_bundle_1.0_community_service_service_1_"
                    "component_Component 1 from Service 1_component_1_1_action"
                ),
                "display_name": (
                    "sample_bundle_1.0_community_service_service_1_"
                    "component_Component 1 from Service 1_component_1_1_action"
                ),
                "bundle": self.bundle_1,
                "type": RoleTypes.HIDDEN,
                "module_name": "rbac.roles",
                "class_name": "ActionRole",
                "init_params": {
                    "action_id": self.component11_action.id,
                    "app_name": "cm",
                    "model": "ServiceComponent",
                    "filter": {
                        "prototype__name": "component_1",
                        "prototype__type": "component",
                        "prototype__bundle_id": self.bundle_1.id,
                    },
                },
                "parametrized_by_type": ["component"],
            },
            {
                "name": (
                    "sample_bundle_1.0_community_service_service_1_"
                    "component_Component 2 from Service 1_component_2_1_action"
                ),
                "display_name": (
                    "sample_bundle_1.0_community_service_service_1_"
                    "component_Component 2 from Service 1_component_2_1_action"
                ),
                "bundle": self.bundle_1,
                "type": RoleTypes.HIDDEN,
                "module_name": "rbac.roles",
                "class_name": "ActionRole",
                "init_params": {
                    "action_id": self.component21_action.id,
                    "app_name": "cm",
                    "model": "ServiceComponent",
                    "filter": {
                        "prototype__name": "component_2",
                        "prototype__type": "component",
                        "prototype__bundle_id": self.bundle_1.id,
                    },
                },
                "parametrized_by_type": ["component"],
            },
            {
                "name": "sample_bundle_1.0_community_service_Service 2_service_2_action",
                "display_name": "sample_bundle_1.0_community_service_Service 2_service_2_action",
                "bundle": self.bundle_1,
                "type": RoleTypes.HIDDEN,
                "module_name": "rbac.roles",
                "class_name": "ActionRole",
                "init_params": {
                    "action_id": self.service2_action.id,
                    "app_name": "cm",
                    "model": "ClusterObject",
                    "filter": {
                        "prototype__name": "service_2",
                        "prototype__type": "service",
                        "prototype__bundle_id": self.bundle_1.id,
                    },
                },
                "parametrized_by_type": ["service"],
            },
            {
                "name": (
                    "sample_bundle_1.0_community_service_service_2_"
                    "component_Component 1 from Service 2_component_1_2_action"
                ),
                "display_name": (
                    "sample_bundle_1.0_community_service_service_2_"
                    "component_Component 1 from Service 2_component_1_2_action"
                ),
                "bundle": self.bundle_1,
                "type": RoleTypes.HIDDEN,
                "module_name": "rbac.roles",
                "class_name": "ActionRole",
                "init_params": {
                    "action_id": self.component12_action.id,
                    "app_name": "cm",
                    "model": "ServiceComponent",
                    "filter": {
                        "prototype__name": "component_1",
                        "prototype__type": "component",
                        "prototype__bundle_id": self.bundle_1.id,
                    },
                },
                "parametrized_by_type": ["component"],
            },
            {
                "name": (
                    "sample_bundle_1.0_community_service_service_2_"
                    "component_Component 2 from Service 2_component_2_2_action"
                ),
                "display_name": (
                    "sample_bundle_1.0_community_service_service_2_"
                    "component_Component 2 from Service 2_component_2_2_action"
                ),
                "bundle": self.bundle_1,
                "type": RoleTypes.HIDDEN,
                "module_name": "rbac.roles",
                "class_name": "ActionRole",
                "init_params": {
                    "action_id": self.component22_action.id,
                    "app_name": "cm",
                    "model": "ServiceComponent",
                    "filter": {
                        "prototype__name": "component_2",
                        "prototype__type": "component",
                        "prototype__bundle_id": self.bundle_1.id,
                    },
                },
                "parametrized_by_type": ["component"],
            },
            # business action roles
            {
                "name": "Cluster Action: Cluster Action",
                "display_name": "Cluster Action: Cluster Action",
                "description": "Cluster Action: Cluster Action",
                "type": RoleTypes.BUSINESS,
                "module_name": "rbac.roles",
                "class_name": "ParentRole",
                "parametrized_by_type": ["cluster"],
            },
            {
                "name": "Service Action: Service 1 Action",
                "display_name": "Service Action: Service 1 Action",
                "description": "Service Action: Service 1 Action",
                "type": RoleTypes.BUSINESS,
                "module_name": "rbac.roles",
                "class_name": "ParentRole",
                "parametrized_by_type": ["service"],
            },
            {
                "name": "Component Action: Component 1 from Service 1 Action",
                "display_name": "Component Action: Component 1 from Service 1 Action",
                "description": "Component Action: Component 1 from Service 1 Action",
                "type": RoleTypes.BUSINESS,
                "module_name": "rbac.roles",
                "class_name": "ParentRole",
                "parametrized_by_type": ["service", "component"],
            },
            {
                "name": "Component Action: Component 2 from Service 1 Action",
                "display_name": "Component Action: Component 2 from Service 1 Action",
                "description": "Component Action: Component 2 from Service 1 Action",
                "type": RoleTypes.BUSINESS,
                "module_name": "rbac.roles",
                "class_name": "ParentRole",
                "parametrized_by_type": ["service", "component"],
            },
            {
                "name": "Service Action: Service 2 Action",
                "display_name": "Service Action: Service 2 Action",
                "description": "Service Action: Service 2 Action",
                "type": RoleTypes.BUSINESS,
                "module_name": "rbac.roles",
                "class_name": "ParentRole",
                "parametrized_by_type": ["service"],
            },
            {
                "name": "Component Action: Component 1 from Service 2 Action",
                "display_name": "Component Action: Component 1 from Service 2 Action",
                "description": "Component Action: Component 1 from Service 2 Action",
                "type": RoleTypes.BUSINESS,
                "module_name": "rbac.roles",
                "class_name": "ParentRole",
                "parametrized_by_type": ["service", "component"],
            },
            {
                "name": "Component Action: Component 2 from Service 2 Action",
                "display_name": "Component Action: Component 2 from Service 2 Action",
                "description": "Component Action: Component 2 from Service 2 Action",
                "type": RoleTypes.BUSINESS,
                "module_name": "rbac.roles",
                "class_name": "ParentRole",
                "parametrized_by_type": ["service", "component"],
            },
        ]

        return roles

    def test_cook_roles(self):
        prepare_action_roles(self.bundle_1)

        self.check_roles()
        self.check_permission()

    def check_permission(self):
        permissions = [
            {
                "content_type": ContentType.objects.get_for_model(Cluster),
                "codename": "run_action_Cluster Action",
                "name": "Can run Cluster Action actions",
            },
            {
                "content_type": ContentType.objects.get_for_model(ClusterObject),
                "codename": "run_action_Service 1 Action",
                "name": "Can run Service 1 Action actions",
            },
            {
                "content_type": ContentType.objects.get_for_model(ClusterObject),
                "codename": "run_action_Service 2 Action",
                "name": "Can run Service 2 Action actions",
            },
            {
                "content_type": ContentType.objects.get_for_model(ServiceComponent),
                "codename": "run_action_Component 1 from Service 1 Action",
                "name": "Can run Component 1 from Service 1 Action actions",
            },
            {
                "content_type": ContentType.objects.get_for_model(ServiceComponent),
                "codename": "run_action_Component 2 from Service 1 Action",
                "name": "Can run Component 2 from Service 1 Action actions",
            },
            {
                "content_type": ContentType.objects.get_for_model(ServiceComponent),
                "codename": "run_action_Component 1 from Service 2 Action",
                "name": "Can run Component 1 from Service 2 Action actions",
            },
            {
                "content_type": ContentType.objects.get_for_model(ServiceComponent),
                "codename": "run_action_Component 2 from Service 2 Action",
                "name": "Can run Component 2 from Service 2 Action actions",
            },
        ]
        for permission_data in permissions:
            self.assertEqual(
                Permission.objects.filter(**permission_data).count(),
                1,
                f"Permission does not exist:\n{json.dumps(permission_data, default=str, indent=2)}",
            )

    def check_roles(self):
        roles = self.make_roles_list()
        for role_data in roles:
            count = Role.objects.filter(**role_data).count()

            self.assertEqual(
                count,
                1,
                f"Role does not exist or not unique: {count} !=  1\n" f"{json.dumps(role_data, indent=2, default=str)}",
            )

            role = Role.objects.filter(**role_data).first()
            if role == RoleTypes.BUSINESS:
                self.assertEqual(role.child.count(), 1, "Role cannot have more than one child.")

            if role == RoleTypes.HIDDEN:
                self.assertFalse(role.child.exists(), "Role cannot have children.")

        ca_role = Role.objects.get(name="Cluster Administrator")

        self.assertEqual(
            ca_role.child.filter(name="Cluster Action: Cluster Action").count(),
            1,
            "Cluster Action: Cluster Action role missing from base role",
        )

        sa_role = Role.objects.get(name="Service Administrator")
        sa_role_count = sa_role.child.filter(
            name__in=[
                "Service Action: Service 1 Action",
                "Component Action: Component 1 from Service 1 Action",
                "Component Action: Component 2 from Service 1 Action",
                "Service Action: Service 2 Action",
                "Component Action: Component 1 from Service 2 Action",
                "Component Action: Component 2 from Service 2 Action",
            ]
        ).count()

        self.assertEqual(sa_role_count, 6, "Roles missing from base roles")


# pylint: disable=too-many-instance-attributes, protected-access
class TestMMRoles(RBACBaseTestCase):
    def setUp(self) -> None:
        init_adcm()
        init_roles()

        self.create_bundles_and_prototypes()
        self.cluster = Cluster.objects.create(name="testcluster", prototype=self.clp)
        self.provider = HostProvider.objects.create(
            name="test_provider",
            prototype=self.provider_prototype,
        )
        self.host = Host.objects.create(fqdn="testhost", prototype=self.host_prototype)
        add_host_to_cluster(self.cluster, self.host)
        self.service = ClusterObject.objects.create(cluster=self.cluster, prototype=self.sp_1)
        self.component = ServiceComponent.objects.create(
            cluster=self.cluster, service=self.service, prototype=self.cop_11
        )

        self.test_user_username = "test_user"
        self.test_user_password = "test_user_password"
        self.test_user = User.objects.create_user(
            username=self.test_user_username,
            password=self.test_user_password,
        )

        self.client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.login()

        self.mm_role_host = role_create(
            name="mm role host",
            display_name="mm role host",
            child=[Role.objects.get(name="Manage Maintenance mode")],
        )
        self.mm_role_cluster = role_create(
            name="mm role cluster",
            display_name="mm role cluster",
            child=[Role.objects.get(name="Manage cluster Maintenance mode")],
        )

    def test_no_roles(self):
        for view_name, url_kwarg_name, obj in (
            ("host-details", "host_id", self.host),
            ("component-details", "component_id", self.component),
            ("service-details", "service_id", self.service),
        ):
            url = reverse(view_name, kwargs={url_kwarg_name: obj.pk})
            response = self.client.get(path=url, content_type=APPLICATION_JSON)
            self.assertEqual(response.status_code, 404)

            with self.assertRaises(PermissionDenied):
                check_custom_perm(self.test_user, "change_maintenance_mode", obj._meta.model_name, obj)

    def test_mm_host_role(self):
        policy_create(name="mm host policy", object=[self.host], role=self.mm_role_host, user=[self.test_user])
        check_custom_perm(self.test_user, "change_maintenance_mode", self.host._meta.model_name, self.host)

        response = self.client.post(
            path=reverse("host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
            format="json",
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, 200)

    def test_mm_cluster_role(self):
        policy_create(
            name="mm cluster policy",
            object=[self.cluster],
            role=self.mm_role_cluster,
            user=[self.test_user],
        )
        check_custom_perm(self.test_user, "change_maintenance_mode", self.host._meta.model_name, self.host)
        check_custom_perm(
            self.test_user,
            "change_maintenance_mode",
            self.component._meta.model_name,
            self.component,
        )
        check_custom_perm(self.test_user, "change_maintenance_mode", self.service._meta.model_name, self.service)

        response = self.client.post(
            path=reverse("host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
            format="json",
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
            format="json",
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
            format="json",
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, 200)

    def test_mm_cl_adm_role(self):
        policy_create(
            name="mm cluster policy",
            object=[self.cluster],
            role=Role.objects.get(name="Cluster Administrator"),
            user=[self.test_user],
        )
        check_custom_perm(self.test_user, "change_maintenance_mode", self.host._meta.model_name, self.host)
        check_custom_perm(
            self.test_user,
            "change_maintenance_mode",
            self.component._meta.model_name,
            self.component,
        )
        check_custom_perm(self.test_user, "change_maintenance_mode", self.service._meta.model_name, self.service)

        response = self.client.post(
            path=reverse("host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
            format="json",
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
            format="json",
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
            format="json",
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, 200)
