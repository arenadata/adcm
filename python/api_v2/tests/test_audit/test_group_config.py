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

from cm.models import Cluster, Component, GroupConfig, Host, HostProvider, Service
from django.contrib.contenttypes.models import ContentType
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from api_v2.tests.base import BaseAPITestCase


class TestGroupConfigAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.cluster_1_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.cluster_1),
            object_id=self.cluster_1.pk,
        )
        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host")
        self.cluster_1_group_config.hosts.add(self.host)
        self.new_host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="new_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.new_host)

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.service_1_group_config = GroupConfig.objects.create(
            name="service_1_group_config",
            object_type=ContentType.objects.get_for_model(self.service_1),
            object_id=self.service_1.pk,
        )
        self.service_1_group_config.hosts.add(self.host)
        self.host_for_service = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_for_service"
        )
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_for_service)

        self.component_1 = Component.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )
        self.component_1_group_config = GroupConfig.objects.create(
            name="component_1_group_config",
            object_type=ContentType.objects.get_for_model(self.component_1),
            object_id=self.component_1.pk,
        )
        self.provider_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.provider),
            object_id=self.provider.pk,
        )
        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_for_service, self.component_1)])
        self.cluster_config_data = {
            "config": {
                "activatable_group": {"integer": 100},
                "boolean": False,
                "group": {"float": 2.1},
                "list": ["value1", "value2", "value3", "value4"],
                "variant_not_strict": "value5",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/boolean": {"isSynchronized": False},
                "/group/float": {"isSynchronized": False},
                "/variant_not_strict": {"isSynchronized": False},
                "/list": {"isSynchronized": False},
                "/activatable_group/integer": {"isSynchronized": False},
            },
            "description": "new config",
        }
        self.service_config_data = {
            "config": {
                "group": {"password": "newpassword"},
                "activatable_group": {"text": "new text"},
                "string": "new string",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/activatable_group/text": {"isSynchronized": False},
                "/group/password": {"isSynchronized": False},
                "/string": {"isSynchronized": False},
            },
            "description": "new config",
        }
        self.component_config_data = {
            "config": {
                "group": {"file": "new content"},
                "activatable_group": {"secretfile": "new content"},
                "secrettext": "new secrettext",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/activatable_group/secretfile": {"isSynchronized": False},
                "/group/file": {"isSynchronized": False},
                "/secrettext": {"isSynchronized": False},
            },
            "description": "new config",
        }
        self.provider_config_data = {
            "config": {
                "group": {"map": {"integer_key": "100", "string_key": "new string"}},
                "activatable_group": {
                    "secretmap": {
                        "integer_key": "100",
                        "string_key": "new string",
                    }
                },
                "json": '{"key": "value", "new key": "new value"}',
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/json": {"isSynchronized": False},
                "/group/map": {"isSynchronized": False},
                "/activatable_group/secretmap": {"isSynchronized": False},
            },
            "description": "new config",
        }

    def test_cluster_create_success(self):
        response = self.client.v2[self.cluster_1, "config-groups"].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_create_incorrect_body_fail(self):
        response = self.client.v2[self.cluster_1, "config-groups"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_create_fail(self):
        response = (self.client.v2 / "clusters" / self.get_non_existent_pk(model=Cluster) / "config-groups").post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_cluster_create_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.cluster_1], role_name="View cluster configurations"):
            response = self.client.v2[self.cluster_1, "config-groups"].post(
                data={"name": "group-config-new", "description": "group-config-new"},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_cluster_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.cluster_1, "config-groups"].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_provider_create_success(self):
        response = self.client.v2[self.provider, "config-groups"].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username="admin",
        )

    def test_provider_create_incorrect_body_fail(self):
        response = self.client.v2[self.provider, "config-groups"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username="admin",
        )

    def test_provider_create_fail(self):
        response = (self.client.v2 / "hostproviders" / self.get_non_existent_pk(model=Cluster) / "config-groups").post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_provider_create_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.provider], role_name="View provider configurations"):
            response = self.client.v2[self.provider, "config-groups"].post(
                data={"name": "group-config-new", "description": "group-config-new"},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username=self.test_user.username,
        )

    def test_provider_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.provider, "config-groups"].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username=self.test_user.username,
        )

    def test_component_create_success(self):
        response = self.client.v2[self.component_1, "config-groups"].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_component_create_incorrect_data_fail(self):
        response = self.client.v2[self.component_1, "config-groups"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_component_create_fail(self):
        response = self.client.v2[
            self.service_1, "components", self.get_non_existent_pk(model=Component), "config-groups"
        ].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_component_create_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=[self.component_1], role_name="View component configurations"
        ):
            response = self.client.v2[self.component_1, "config-groups"].post(
                data={"name": "group-config-new", "description": "group-config-new"},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_component_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.component_1, "config-groups"].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_service_create_success(self):
        response = self.client.v2[self.service_1, "config-groups"].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_service_create_incorrect_data_fail(self):
        response = self.client.v2[self.service_1, "config-groups"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_service_create_fail(self):
        response = self.client.v2[
            self.cluster_1, "services", self.get_non_existent_pk(model=Service), "config-groups"
        ].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_service_create_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.service_1], role_name="View service configurations"):
            response = self.client.v2[self.service_1, "config-groups"].post(
                data={"name": "group-config-new", "description": "group-config-new"},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_service_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.service_1, "config-groups"].post(
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_cluster_delete_success(self):
        response = self.client.v2[self.cluster_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_delete_fail(self):
        response = self.client.v2[self.cluster_1, "config-groups", self.get_non_existent_pk(model=GroupConfig)].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_delete_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.cluster_1], role_name="View cluster configurations"):
            response = self.client.v2[self.cluster_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_cluster_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.cluster_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_provider_delete_success(self):
        response = self.client.v2[self.provider_group_config].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name=f"{self.provider_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username="admin",
        )

    def test_provider_delete_fail(self):
        response = self.client.v2[self.provider, "config-groups", self.get_non_existent_pk(model=GroupConfig)].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username="admin",
        )

    def test_provider_delete_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.provider], role_name="View provider configurations"):
            response = self.client.v2[self.provider_group_config].delete()
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username=self.test_user.username,
        )

    def test_provider_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.provider_group_config].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username=self.test_user.username,
        )

    def test_service_delete_success(self):
        response = self.client.v2[self.service_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name=f"{self.service_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_service_delete_fail(self):
        response = self.client.v2[self.service_1, "config-groups", self.get_non_existent_pk(model=GroupConfig)].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_service_delete_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.service_1], role_name="View service configurations"):
            response = self.client.v2[self.service_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.service_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_service_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.service_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.service_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_component_delete_success(self):
        response = self.client.v2[self.component_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name=f"{self.component_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_component_delete_fail(self):
        response = self.client.v2[
            self.component_1, "config-groups", self.get_non_existent_pk(model=GroupConfig)
        ].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_component_delete_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=[self.component_1], role_name="View component configurations"
        ):
            response = self.client.v2[self.component_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.component_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_component_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.component_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.component_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_cluster_update_success(self):
        response = self.client.v2[self.cluster_1_group_config].patch(data={})
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_update_incorrect_body_fail(self):
        response = self.client.v2[self.cluster_1_group_config].patch(
            data={"name": {}},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_update_fail(self):
        response = self.client.v2[self.cluster_1, "config-groups", self.get_non_existent_pk(model=GroupConfig)].patch(
            data={}
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_update_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.cluster_1], role_name="View cluster configurations"):
            response = self.client.v2[self.cluster_1_group_config].patch(data={})
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_cluster_update_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.cluster_1_group_config].patch(data={})
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_cluster_config_create_success(self):
        response = self.client.v2[self.cluster_1_group_config, "configs"].post(
            data=self.cluster_config_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_config_create_incorrect_data_fail(self):
        response = self.client.v2[self.cluster_1_group_config, "configs"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_config_create_fail(self):
        response = (
            self.client.v2
            / "clusters"
            / self.get_non_existent_pk(model=Cluster)
            / "config-groups"
            / self.cluster_1_group_config.pk
            / "configs"
        ).post(
            data=self.cluster_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_cluster_config_create_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.cluster_1], role_name="View cluster configurations"):
            response = self.client.v2[self.cluster_1_group_config, "configs"].post(
                data=self.cluster_config_data,
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_cluster_config_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.cluster_1_group_config, "configs"].post(
            data=self.cluster_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_service_config_create_success(self):
        response = self.client.v2[self.service_1_group_config, "configs"].post(
            data=self.service_config_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_service_config_create_incorrect_data_fail(self):
        response = self.client.v2[self.service_1_group_config, "configs"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_service_config_create_fail(self):
        response = self.client.v2[
            self.cluster_1, "services", 1000, "config-groups", self.service_1_group_config.pk, "configs"
        ].post(
            data=self.service_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_service_config_create_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.service_1], role_name="View service configurations"):
            response = self.client.v2[self.service_1_group_config, "configs"].post(
                data=self.service_config_data,
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_service_config_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.service_1_group_config, "configs"].post(
            data=self.service_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_component_config_create_success(self):
        response = self.client.v2[self.component_1_group_config, "configs"].post(
            data=self.component_config_data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"{self.component_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_component_config_create_incorrect_data_fail(self):
        response = self.client.v2[self.component_1_group_config, "configs"].post(
            data={"config": {}, "adcmMeta": {}},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"{self.component_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_component_config_create_fail(self):
        response = self.client.v2[
            self.cluster_1,
            "services",
            self.service_1.pk,
            "components",
            1000,
            "config-groups",
            self.component_1_group_config.pk,
            "configs",
        ].post(
            data=self.component_config_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.component_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_component_config_create_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=[self.component_1], role_name="View component configurations"
        ):
            response = self.client.v2[self.component_1_group_config, "configs"].post(
                data=self.component_config_data,
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.component_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_component_config_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.component_1_group_config, "configs"].post(
            data=self.component_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.component_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_hostprovider_config_create_success(self):
        response = self.client.v2[self.provider_group_config, "configs"].post(
            data=self.provider_config_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username="admin",
        )

    def test_hostprovider_config_create_incorrect_data_fail(self):
        response = self.client.v2[self.provider_group_config, "configs"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username="admin",
        )

    def test_hostprovider_config_create_fail(self):
        response = (
            self.client.v2
            / "hostproviders"
            / self.get_non_existent_pk(model=HostProvider)
            / "config-groups"
            / self.provider_group_config.pk
            / "configs"
        ).post(
            data=self.provider_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_hostprovider_config_create_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.provider], role_name="View provider configurations"):
            response = self.client.v2[self.provider_group_config, "configs"].post(
                data=self.provider_config_data,
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username=self.test_user.username,
        )

    def test_hostprovider_config_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.provider_group_config, "configs"].post(
            data=self.provider_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username=self.test_user.username,
        )

    def test_provider_add_host_success(self):
        response = self.client.v2[self.provider_group_config, "hosts"].post(
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"{self.new_host.fqdn} host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username="admin",
        )

    def test_provider_add_host_incorrect_data_fail(self):
        response = self.client.v2[self.provider_group_config, "hosts"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username="admin",
        )

    def test_provider_add_host_fail(self):
        response = self.client.v2[
            self.provider, "config-groups", self.get_non_existent_pk(model=GroupConfig), "hosts"
        ].post(
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.new_host.fqdn} host added to configuration group",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username="admin",
        )

    def test_provider_add_host_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.provider], role_name="View provider configurations"):
            response = self.client.v2[self.provider_group_config, "hosts"].post(
                data={"hostId": self.new_host.pk},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.new_host.fqdn} host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username=self.test_user.username,
        )

    def test_provider_add_host_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.provider_group_config, "hosts"].post(
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.new_host.fqdn} host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username=self.test_user.username,
        )

    def test_service_add_host_success(self):
        response = self.client.v2[self.service_1_group_config, "hosts"].post(
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_service_add_host_fail(self):
        response = self.client.v2[
            self.cluster_1,
            "services",
            self.get_non_existent_pk(model=Service),
            "config-groups",
            self.service_1_group_config,
            "hosts",
        ].post(
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_service_add_host_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[self.service_1], role_name="View service configurations"):
            response = self.client.v2[self.service_1_group_config, "hosts"].post(
                data={"hostId": self.host_for_service.pk},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_service_add_host_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.service_1_group_config, "hosts"].post(
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username=self.test_user.username,
        )

    def test_cluster_add_host_success(self):
        response = self.client.v2[self.cluster_1_group_config, "hosts"].post(
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_add_host_incorrect_data_fail(self):
        response = self.client.v2[self.cluster_1_group_config, "hosts"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_add_host_fail(self):
        response = (
            self.client.v2
            / "clusters"
            / self.get_non_existent_pk(model=Cluster)
            / "config-groups"
            / self.cluster_1_group_config
            / "hosts"
        ).post(
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_cluster_add_host_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[self.cluster_1], role_name="View cluster configurations"):
            response = self.client.v2[self.cluster_1_group_config, "hosts"].post(
                data={"hostId": self.new_host.pk},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_cluster_add_host_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.cluster_1_group_config, "hosts"].post(
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_component_add_host_success(self):
        response = self.client.v2[self.component_1_group_config, "hosts"].post(
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_component_add_host_incorrect_data_fail(self):
        response = self.client.v2[self.component_1_group_config, "hosts"].post(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"host added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_component_add_host_fail(self):
        response = self.client.v2[
            self.service_1,
            "components",
            self.get_non_existent_pk(model=Component),
            "config-groups",
            self.component_1_group_config,
            "hosts",
        ].post(
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_component_add_host_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=[self.component_1], role_name="View component configurations"
        ):
            response = self.client.v2[self.component_1_group_config, "hosts"].post(
                data={"hostId": self.host_for_service.pk},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_component_add_host_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.component_1_group_config, "hosts"].post(
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username=self.test_user.username,
        )

    def test_component_remove_host_success(self):
        self.component_1_group_config.hosts.add(self.host_for_service)

        response = self.client.v2[self.component_1_group_config, "hosts", self.host_for_service.pk].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"removed from {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.component_1),
            user__username="admin",
        )

    def test_service_remove_host_not_found_fail(self):
        self.service_1_group_config.hosts.add(self.host_for_service)

        response = self.client.v2[self.service_1_group_config, "hosts", self.get_non_existent_pk(model=Host)].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"host removed from {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_service_remove_host_group_found_host_not_found_fail(self):
        self.service_1_group_config.hosts.add(self.host_for_service)

        response = self.client.v2[self.service_1, "config-groups", 1000, "hosts", self.host_for_service].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host removed from configuration group",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.service_1),
            user__username="admin",
        )

    def test_cluster_remove_host_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        self.cluster_1_group_config.hosts.add(self.host_for_service)

        response = self.client.v2[self.cluster_1_group_config, "hosts", self.host_for_service.pk].delete()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host removed "
            f"from {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_hostprovider_remove_host_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)
        self.provider_group_config.hosts.add(self.host_for_service)

        with self.grant_permissions(to=self.test_user, on=[self.provider], role_name="View provider configurations"):
            response = self.client.v2[self.provider_group_config, "hosts", self.host_for_service.pk].delete()
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.host_for_service.fqdn} host removed "
            f"from {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.provider),
            user__username=self.test_user.username,
        )
