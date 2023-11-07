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

from api_v2.tests.base import BaseAPITestCase
from audit.models import AuditObjectType
from cm.models import GroupConfig, ServiceComponent
from django.contrib.contenttypes.models import ContentType
from rbac.services.user import create_user
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)


class TestGroupConfigAudit(BaseAPITestCase):  # pylint: disable=too-many-public-methods,too-many-instance-attributes
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        self.cluster_1_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.cluster_1),
            object_id=self.cluster_1.pk,
        )
        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host")
        self.cluster_1_group_config.hosts.add(self.host)
        self.new_host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="new_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.new_host)

        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
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

        self.component_1 = ServiceComponent.objects.get(
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
        self.add_hostcomponent_map(
            cluster=self.cluster_1,
            hc_map=[
                {
                    "host_id": self.host_for_service.pk,
                    "service_id": self.service_1.pk,
                    "component_id": self.component_1.pk,
                }
            ],
        )
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
        response = self.client.post(
            path=reverse(viewname="v2:cluster-group-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_create_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-group-config-list", kwargs={"cluster_pk": 1000}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            object_changes={},
            audit_object__isnull=True,
            user__username="admin",
        )

    def test_cluster_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(viewname="v2:cluster-group-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_provider_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:hostprovider-group-config-list", kwargs={"hostprovider_pk": self.provider.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type=AuditObjectType.PROVIDER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_provider_create_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:hostprovider-group-config-list", kwargs={"hostprovider_pk": 1000}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_provider_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(viewname="v2:hostprovider-group-config-list", kwargs={"hostprovider_pk": self.provider.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_component_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type=AuditObjectType.COMPONENT,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_component_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": 1000,
                },
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_component_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_service_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type=AuditObjectType.SERVICE,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_service_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": 1000},
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_service_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_cluster_delete_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_delete_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": 1000},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_cluster_delete_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_provider_delete_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:hostprovider-group-config-detail",
                kwargs={"hostprovider_pk": self.cluster_1.pk, "pk": self.provider_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"{self.provider_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type=AuditObjectType.PROVIDER,
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_provider_delete_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:hostprovider-group-config-detail",
                kwargs={"hostprovider_pk": self.cluster_1.pk, "pk": 1000},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_provider_delete_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(
                viewname="v2:hostprovider-group-config-detail",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_service_delete_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.service_1_group_config.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type=AuditObjectType.SERVICE,
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_service_delete_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk, "pk": 1000},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_service_delete_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.service_1_group_config.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_component_delete_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:component-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.component_1_group_config.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"{self.component_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type=AuditObjectType.COMPONENT,
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_component_delete_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:component-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": 1000,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_component_delete_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(
                viewname="v2:component-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.component_1_group_config.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_cluster_update_success(self):
        response = self.client.patch(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_update_fail(self):
        response = self.client.patch(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": 1000},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group updated",
            operation_type="update",
            operation_result="fail",
            user__username="admin",
        )

    def test_cluster_update_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.patch(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_cluster_config_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data=self.cluster_config_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_config_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": 1000, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data=self.cluster_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_cluster_config_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data=self.cluster_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_service_config_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data=self.service_config_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type=AuditObjectType.SERVICE,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_service_config_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": 1000,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data=self.service_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_service_config_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data=self.service_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_component_config_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data=self.component_config_data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.component_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type=AuditObjectType.COMPONENT,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_component_config_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": 1000,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data=self.component_config_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_component_config_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data=self.component_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.component_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_hostprovider_config_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "group_config_pk": self.provider_group_config.pk,
                },
            ),
            data=self.provider_config_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type=AuditObjectType.PROVIDER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_hostprovider_config_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={
                    "hostprovider_pk": 1000,
                    "group_config_pk": self.provider_group_config.pk,
                },
            ),
            data=self.provider_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_hostprovider_config_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "group_config_pk": self.provider_group_config.pk,
                },
            ),
            data=self.provider_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_provider_add_host_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-hosts-list",
                kwargs={"hostprovider_pk": self.provider.pk, "group_config_pk": self.provider_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type=AuditObjectType.PROVIDER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_provider_add_host_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-hosts-list",
                kwargs={"hostprovider_pk": 1000, "group_config_pk": self.provider_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_provider_add_host_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-hosts-list",
                kwargs={"hostprovider_pk": self.provider.pk, "group_config_pk": self.provider_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_service_add_host_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type=AuditObjectType.SERVICE,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_service_add_host_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": 1000,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_service_add_host_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_cluster_add_host_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-hosts-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_add_host_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-hosts-list",
                kwargs={"cluster_pk": 1000, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_cluster_add_host_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-hosts-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_component_add_host_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type=AuditObjectType.COMPONENT,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_component_add_host_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": 1000,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_component_add_host_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )
