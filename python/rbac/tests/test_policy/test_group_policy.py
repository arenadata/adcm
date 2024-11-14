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

from pathlib import Path

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import Action, Component, ConfigLog, ObjectType
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from rbac.models import Group


class GroupPolicyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        group_1 = self.get_new_group(name="group_1")
        group_2 = self.get_new_group(name="group_2")

        self.user_1_password = "user_1_password"
        self.user_1 = self.get_new_user(
            username="user_1",
            password=self.user_1_password,
            group_pk=group_1.pk,
        )
        self.get_new_user(username="user_2", password="user_2_password", group_pk=group_2.pk)

        cluster = self.get_cluster()

        self.main_with_components_service = self.create_service(cluster_pk=cluster.pk, name="main_with_components")
        control_with_components_service = self.create_service(cluster_pk=cluster.pk, name="control_with_components")

        self.create_policy(
            role_name="Service Administrator",
            obj=self.main_with_components_service,
            group_pk=group_1.pk,
        )
        self.create_policy(
            role_name="Service Administrator",
            obj=control_with_components_service,
            group_pk=group_2.pk,
        )

        provider = self.create_provider(
            bundle_path=self.base_dir / "python" / "rbac" / "tests" / "files" / "provider.tar",
            name="Test Provider",
        )
        host_1 = self.create_host_in_cluster(provider_pk=provider.pk, name="host-1", cluster_pk=cluster.pk)
        host_2 = self.create_host_in_cluster(provider_pk=provider.pk, name="host-2", cluster_pk=cluster.pk)

        self.create_hostcomponent(
            cluster_pk=cluster.pk,
            hostcomponent_data=self.get_hostcomponent_data(
                service_pk=self.main_with_components_service.pk,
                host_pk=host_1.pk,
            ),
        )
        self.create_hostcomponent(
            cluster_pk=cluster.pk,
            hostcomponent_data=self.get_hostcomponent_data(
                service_pk=control_with_components_service.pk,
                host_pk=host_2.pk,
            ),
        )

    def get_cluster(self):
        cluster_bundle = self.upload_and_load_bundle(
            path=Path(
                self.base_dir,
                "python/rbac/tests/files/bundle_10.tar",
            ),
        )

        return self.create_cluster(bundle_pk=cluster_bundle.pk, name="Test Cluster")

    def get_new_group(self, name: str) -> Group:
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:group-list"),
            data={"name": name},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return Group.objects.get(pk=response.json()["id"])

    def test_user_can_update_service_config_via_group_policy(self):
        config_log = ConfigLog.objects.get(
            obj_ref=self.main_with_components_service.config,
            id=self.main_with_components_service.config.current,
        )
        config_log.config["param"] = "new"

        with self.another_user_logged_in(username=self.user_1.username, password=self.user_1_password):
            response: Response = self.client.post(
                path=reverse(viewname="v1:config-history", kwargs={"service_id": self.main_with_components_service.pk}),
                data={"config": config_log.config},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)


class DeleteServicePolicyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.user_1_password = "user_1_password"
        self.user_1_group = Group.objects.create(name="user_1_group")
        self.user_2_group = Group.objects.create(name="user_2_group")
        self.user_1 = self.get_new_user(username="user_1", password=self.user_1_password, group_pk=self.user_1_group.pk)
        self.get_new_user(username="user_2", password="user_2_password", group_pk=self.user_2_group.pk)

        self.cluster = self.get_cluster()

        self.main_with_components_service = self.create_service(cluster_pk=self.cluster.pk, name="main_with_components")

        self.create_policy(
            role_name="Cluster Administrator",
            obj=self.cluster,
            group_pk=self.user_1_group.pk,
        )
        self.service_admin_policy_pk = self.create_policy(
            role_name="Service Administrator",
            obj=self.main_with_components_service,
            group_pk=self.user_2_group.pk,
        )

    def get_cluster(self):
        cluster_bundle = self.upload_and_load_bundle(
            path=Path(
                self.base_dir,
                "python/rbac/tests/files/bundle_10.tar",
            ),
        )

        return self.create_cluster(bundle_pk=cluster_bundle.pk, name="Test Cluster")

    def test_user_can_update_service_config_after_undelete(self):
        response = self.client.delete(
            path=reverse(viewname="v1:service-details", kwargs={"service_id": self.main_with_components_service.pk}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        main_with_components_service = self.create_service(cluster_pk=self.cluster.pk, name="main_with_components")

        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:policy-detail", kwargs={"pk": self.service_admin_policy_pk}),
            data={
                "object": [
                    {
                        "name": main_with_components_service.name,
                        "type": ObjectType.SERVICE,
                        "id": main_with_components_service.pk,
                    }
                ],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        config_log = ConfigLog.objects.get(
            obj_ref=main_with_components_service.config,
            id=main_with_components_service.config.current,
        )
        config_log.config["param"] = "new"

        with self.another_user_logged_in(username=self.user_1.username, password=self.user_1_password):
            response: Response = self.client.post(
                path=reverse(viewname="v1:config-history", kwargs={"service_id": main_with_components_service.pk}),
                data={"config": config_log.config},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)


class ActionsPolicyTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.user_1_password = "user_1_password"
        self.user_1_group = Group.objects.create(name="user_1_group")
        self.user_1 = self.get_new_user(username="user_1", password=self.user_1_password, group_pk=self.user_1_group.pk)

        cluster = self.get_cluster()
        action_service = self.create_service(cluster_pk=cluster.pk, name="actions_service")
        component = Component.objects.get(prototype__name="single_component")

        provider = self.create_provider(
            bundle_path=self.base_dir / "python" / "rbac" / "tests" / "files" / "provider.tar",
            name="Test Provider",
        )
        self.host_1 = self.create_host_in_cluster(provider_pk=provider.pk, name="host-1", cluster_pk=cluster.pk)
        self.create_hostcomponent(
            cluster_pk=cluster.pk,
            hostcomponent_data=[
                {"component_id": component.pk, "host_id": self.host_1.pk, "service_id": action_service.pk}
            ],
        )

        user_1_role_name = "user_1_role"
        self.create_role(
            role_name=user_1_role_name,
            parametrized_by_type=[ObjectType.CLUSTER, ObjectType.SERVICE, ObjectType.COMPONENT, ObjectType.HOST],
            children_names=[
                "Cluster Action: Cluster ready for host",
                "Service Action: Service ready for host",
                "Component Action: Component ready for host",
            ],
        )

        self.create_policy(
            role_name=user_1_role_name,
            obj=cluster,
            group_pk=self.user_1_group.pk,
        )

    def get_cluster(self):
        cluster_bundle = self.upload_and_load_bundle(
            path=Path(
                self.base_dir,
                "python/rbac/tests/files/case3.tar",
            ),
        )

        return self.create_cluster(bundle_pk=cluster_bundle.pk, name="Test Cluster")

    def test_user_can_run_action(self):
        action = Action.objects.get(display_name="Cluster ready for host")
        with self.another_user_logged_in(username=self.user_1.username, password=self.user_1_password):
            response: Response = self.client.post(
                path=reverse(viewname="v1:run-task", kwargs={"host_id": self.host_1.pk, "action_id": action.pk}),
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
