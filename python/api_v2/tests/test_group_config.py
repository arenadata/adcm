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

from operator import attrgetter, itemgetter
from typing import Iterable, NamedTuple, TypeAlias

from adcm.tests.client import WithID
from cm.converters import orm_object_to_core_type
from cm.models import Cluster, ClusterObject, ConfigLog, GroupConfig, Host, HostProvider, ServiceComponent
from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase

CONFIG_GROUPS = "config-groups"
HOST_CANDIDATES = "host-candidates"

ObjectWithConfigHostGroup: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider


class BaseClusterGroupConfigTestCase(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_1_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.cluster_1),
            object_id=self.cluster_1.pk,
        )
        self.host_fqdn = "host"
        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn=self.host_fqdn)
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.cluster_1_group_config.hosts.add(self.host)
        self.new_host_fqdn = "new_host"
        self.new_host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn=self.new_host_fqdn)
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.new_host)

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.service_2 = self.add_services_to_cluster(service_names=["service_2"], cluster=self.cluster_1).get()
        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)


class BaseServiceGroupConfigTestCase(BaseClusterGroupConfigTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1_group_config = GroupConfig.objects.create(
            name="service_1_group_config",
            object_type=ContentType.objects.get_for_model(self.service_1),
            object_id=self.service_1.pk,
        )
        self.service_2_group_config = GroupConfig.objects.create(
            name="service_2_group_config",
            object_type=ContentType.objects.get_for_model(self.service_2),
            object_id=self.service_2.pk,
        )
        self.host_for_service = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_for_service"
        )
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_for_service)
        self.host_in_cluster = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_in_cluster", cluster=self.cluster_1
        )

        self.component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )
        self.component_2 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_2"
        )
        self.set_hostcomponent(
            cluster=self.cluster_1, entries=[(self.host, self.component_1), (self.host_for_service, self.component_1)]
        )
        self.service_1_group_config.hosts.add(self.host)


class TestGroupConfigNaming(BaseServiceGroupConfigTestCase):
    def test_create_group_with_same_name_for_different_entities_of_same_type_success(self) -> None:
        service_2 = self.add_services_to_cluster(service_names=["service_1_clone"], cluster=self.cluster_1).get()
        component_of_service_2 = ServiceComponent.objects.get(service=service_2, prototype__name=self.component_1.name)

        with self.subTest("Cluster"):
            self.assertEqual(GroupConfig.objects.filter(name=self.cluster_1_group_config.name).count(), 1)

            response = self.client.v2[self.cluster_2, CONFIG_GROUPS].post(
                data={"name": self.cluster_1_group_config.name, "description": "group-config-new"},
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(GroupConfig.objects.filter(name=self.cluster_1_group_config.name).count(), 2)

        with self.subTest("Service"):
            self.assertEqual(GroupConfig.objects.filter(name=self.service_1_group_config.name).count(), 1)

            response = self.client.v2[service_2, CONFIG_GROUPS].post(
                data={"name": self.service_1_group_config.name, "description": "group-config-new"}
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(GroupConfig.objects.filter(name=self.service_1_group_config.name).count(), 2)

        with self.subTest("Component"):
            name = "component_group"
            self.assertEqual(GroupConfig.objects.filter(name=name).count(), 0)

            response = self.client.v2[component_of_service_2, CONFIG_GROUPS].post(
                data={"name": name, "description": "group-config-new"}
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(GroupConfig.objects.filter(name=name).count(), 1)

            response = self.client.v2[self.component_1, CONFIG_GROUPS].post(
                data={"name": name, "description": "group-config-new"}
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(GroupConfig.objects.filter(name=name).count(), 2)


class TestClusterGroupConfig(BaseClusterGroupConfigTestCase):
    def test_list_success(self):
        response = self.client.v2[self.cluster_1, CONFIG_GROUPS].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.cluster_1_group_config.pk)

    def test_retrieve_success(self):
        response = self.client.v2[self.cluster_1_group_config].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.cluster_1_group_config.pk)

    def test_create_success(self):
        response = self.client.v2[self.cluster_1, CONFIG_GROUPS].post(
            data={"name": "group-config-new", "description": "group-config-new"}
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()["name"], "group-config-new")

    def test_create_no_permissions_fail(self):
        initial_group_config_ids = set(GroupConfig.objects.values_list("id", flat=True))

        user_password = "user_password"
        user_with_view_rights = self.create_user(username="user_with_view_rights", password=user_password)
        with self.grant_permissions(
            to=user_with_view_rights, on=self.cluster_1, role_name="View cluster configurations"
        ):
            self.client.login(username=user_with_view_rights.username, password=user_password)

            response = self.client.v2[self.cluster_1_group_config].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.v2[self.cluster_1, CONFIG_GROUPS].post(
                data={"name": "group-config-new", "description": "group-config-new"},
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertSetEqual(initial_group_config_ids, set(GroupConfig.objects.values_list("id", flat=True)))

    def test_delete_success(self):
        response = self.client.v2[self.cluster_1_group_config].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_list_hosts_success(self):
        response = self.client.v2[self.cluster_1_group_config, "hosts"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_add_host_success(self):
        response = self.client.v2[self.cluster_1_group_config, "hosts"].post(data={"hostId": self.new_host.pk})

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertDictEqual(response.json(), {"id": 2, "name": "new_host"})

    def test_add_host_from_another_group_config_fail(self):
        new_group_config = GroupConfig.objects.create(
            name="new_group_config",
            object_type=ContentType.objects.get_for_model(self.cluster_1),
            object_id=self.cluster_1.pk,
        )

        response = self.client.v2[new_group_config, "hosts"].post(data={"hostId": self.host.pk})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "GROUP_CONFIG_HOST_ERROR",
                "desc": (
                    "host is not available for this object,"
                    " or host already is a member of another group of this object"
                ),
                "level": "error",
            },
        )

    def test_host_candidates(self):
        with self.subTest("Group"):
            response = self.client.v2[self.cluster_1_group_config, "host-candidates"].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(len(response.json()), 1)
            self.assertEqual(response.json()[0]["name"], self.new_host.name)

        with self.subTest("Own Group"):
            response = self.client.v2[self.cluster_1, CONFIG_GROUPS, "host-candidates"].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(len(response.json()), 1)
            self.assertEqual(response.json()[0]["name"], self.new_host.name)

        new_host = self.add_host(provider=self.provider, fqdn="new-host", cluster=self.cluster_1)
        response = self.client.v2[self.cluster_1_group_config, "hosts"].post(data={"hostId": self.new_host.pk})
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        with self.subTest("Own Group When One Added To Group"):
            response = self.client.v2[self.cluster_1, CONFIG_GROUPS, "host-candidates"].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(len(response.json()), 1)
            self.assertEqual(response.json()[0]["name"], new_host.name)

    def test_delete_host_success(self):
        response = self.client.v2[self.cluster_1_group_config, "hosts", self.host].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(self.host, Host.objects.get(id=self.host.pk))
        self.assertNotIn(self.host, self.cluster_1_group_config.hosts.all())

    def test_adcm_5199_config_description_inheritance(self):
        config_data = {
            "config": {
                "activatable_group": {"integer": 500},
                "boolean": False,
                "group": {"float": 2.7},
                "list": ["value1", "value23", "value32", "value44"],
                "variant_not_strict": "value55",
            },
            "adcmMeta": {"/activatable_group": {"isActive": False}},
            "description": "new description",
        }

        response = self.client.v2[self.cluster_1, CONFIG_GROUPS].post(
            data={"name": "Test group config", "description": ""}
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        group_config = GroupConfig.objects.get(pk=response.json()["id"])
        self.assertEqual(ConfigLog.objects.get(pk=group_config.config.current).description, "init")

        response = self.client.v2[self.cluster_1, "configs"].post(data=config_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        group_config.refresh_from_db()
        self.assertEqual(ConfigLog.objects.get(pk=group_config.config.current).description, config_data["description"])

    def test_permissions_another_model_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object configuration"):
            response = self.client.v2[self.cluster_1, CONFIG_GROUPS].get()

            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_permissions_another_object_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Cluster Administrator"):
            response = self.client.v2[self.cluster_1, CONFIG_GROUPS].get()

            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_permissions_another_object_role_create_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Cluster Administrator"):
            response = self.client.v2[self.cluster_1, CONFIG_GROUPS].post(
                data={"name": "group-config-new", "description": "group-config-new"}
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_permissions_another_object_role_create_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
            response = self.client.v2[self.cluster_1, CONFIG_GROUPS].post(data={})

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_another_object_role_retrieve_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
            response = self.client.v2[self.cluster_1_group_config].get()

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_another_object_role_list_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
            response = self.client.v2[self.cluster_1, CONFIG_GROUPS].get()

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)


class TestServiceGroupConfig(BaseServiceGroupConfigTestCase):
    def test_list_success(self):
        response = self.client.v2[self.service_1, CONFIG_GROUPS].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.service_1_group_config.pk)

    def test_retrieve_success(self):
        response = self.client.v2[self.service_1_group_config].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.service_1_group_config.pk)

    def test_create_success(self):
        response = self.client.v2[self.service_1, CONFIG_GROUPS].post(
            data={"name": "service-group-config-new", "description": "service-group-config-new"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()["name"], "service-group-config-new")

    def test_adcm_5285_create_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
            response = self.client.v2[self.service_1, CONFIG_GROUPS].post(
                data={"name": "service-group-config-new", "description": "service-group-config-new"},
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(response.json()["name"], "service-group-config-new")

    def test_create_no_permissions_fail(self):
        initial_group_config_ids = set(GroupConfig.objects.values_list("id", flat=True))

        user_password = "user_password"
        user_with_view_rights = self.create_user(username="user_with_view_rights", password=user_password)
        with self.grant_permissions(
            to=user_with_view_rights, on=self.service_1, role_name="View service configurations"
        ):
            self.client.login(username=user_with_view_rights.username, password=user_password)

            response = self.client.v2[self.service_1_group_config].get()

            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.v2[self.service_1, CONFIG_GROUPS].post(
                data={"name": "group-config-new", "description": "group-config-new"},
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertSetEqual(initial_group_config_ids, set(GroupConfig.objects.values_list("id", flat=True)))

    def test_adcm_5285_edit_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
            response = self.client.v2[self.service_1, CONFIG_GROUPS].post(
                data={"name": "service-group-config-new", "description": "service-group-config-new"},
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)

            group_config = GroupConfig.objects.get(pk=response.json()["id"])

            new_config = {
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

            response = self.client.v2[group_config, "configs"].post(data=new_config)

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(response.json()["description"], "new config")

    def test_adcm_5113_create_success(self):
        service_config_data = {
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

        service_new_group_config = GroupConfig.objects.create(
            name="service_new_group_config",
            object_type=ContentType.objects.get_for_model(self.service_1),
            object_id=self.service_1.pk,
        )

        config_log_to_delete = ConfigLog.objects.filter(pk=service_new_group_config.pk).last()
        config_log_to_delete.delete()

        response = self.client.v2[service_new_group_config, "configs"].post(data=service_config_data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_adcm_5113_twice_create_success(self):
        service_config_data_1 = {
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
        service_config_data_2 = {
            "config": {
                "group": {"password": "newpassword2"},
                "activatable_group": {"text": "new text 2"},
                "string": "new string 2",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/activatable_group/text": {"isSynchronized": False},
                "/group/password": {"isSynchronized": False},
                "/string": {"isSynchronized": False},
            },
            "description": "new config 2",
        }

        service_new_group_config_1 = GroupConfig.objects.create(
            name="service_new_group_config_1",
            object_type=ContentType.objects.get_for_model(self.service_1),
            object_id=self.service_1.pk,
        )
        service_new_group_config_2 = GroupConfig.objects.create(
            name="service_new_group_config_2",
            object_type=ContentType.objects.get_for_model(self.service_1),
            object_id=self.service_1.pk,
        )

        config_logs_to_delete = ConfigLog.objects.filter(
            pk__in=(service_new_group_config_1.pk, service_new_group_config_2.pk)
        )
        config_logs_to_delete.first().delete()
        config_logs_to_delete.last().delete()

        response = self.client.v2[service_new_group_config_1, "configs"].post(data=service_config_data_1)

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.v2[service_new_group_config_2, "configs"].post(data=service_config_data_2)

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_delete_success(self):
        response = self.client.v2[self.service_1_group_config].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response = self.client.v2[self.service_1_group_config].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_adcm_5285_delete_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
            response = self.client.v2[self.service_1_group_config].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

            response = self.client.v2[self.service_1_group_config].get()
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_list_hosts_success(self):
        response = self.client.v2[self.service_1_group_config, "hosts"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], self.host.name)

    def test_add_host_success(self):
        response = self.client.v2[self.service_1_group_config, "hosts"].post(data={"hostId": self.host_for_service.pk})

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertDictEqual(response.json(), {"id": 3, "name": "host_for_service"})

    def test_add_not_mapped_host_fail(self):
        initial_hosts_count = self.service_1_group_config.hosts.count()

        response = self.client.v2[self.service_1_group_config, "hosts"].post(data={"hostId": self.host_in_cluster.pk})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "GROUP_CONFIG_HOST_ERROR",
                "level": "error",
                "desc": "host is not available for this object, "
                "or host already is a member of another group of this object",
            },
        )
        self.assertEqual(self.service_1_group_config.hosts.count(), initial_hosts_count)

    def test_delete_host_success(self):
        response = self.client.v2[self.service_1_group_config, "hosts", self.host].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(self.host, Host.objects.get(id=self.host.pk))
        self.assertIn(self.host, self.cluster_1_group_config.hosts.all())
        self.assertNotIn(self.host, self.service_1_group_config.hosts.all())

    def test_host_candidates_success(self):
        response = self.client.v2[self.service_1_group_config, "host-candidates"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], self.host_for_service.name)

    def test_adcm_5199_config_description_inheritance(self):
        config_data = {
            "config": {
                "group": {"password": "new_password"},
                "activatable_group": {"text": "new_text"},
                "string": "new_string",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config description",
        }

        response = self.client.v2[self.service_1, CONFIG_GROUPS].post(
            data={"name": "Test group config", "description": ""}
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        group_config = GroupConfig.objects.get(pk=response.json()["id"])
        self.assertEqual(ConfigLog.objects.get(pk=group_config.config.current).description, "init")

        response = self.client.v2[self.service_1, "configs"].post(data=config_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        group_config.refresh_from_db()
        self.assertEqual(ConfigLog.objects.get(pk=group_config.config.current).description, config_data["description"])

    def test_permissions_another_model_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object configuration"):
            response = self.client.v2[self.service_1, CONFIG_GROUPS].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_permissions_another_object_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Cluster Administrator"):
            response = self.client.v2[self.service_1, CONFIG_GROUPS].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_permissions_another_object_role_create_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Cluster Administrator"):
            response = self.client.v2[self.service_2, CONFIG_GROUPS].post(
                data={"name": "service-group-config-new", "description": "service-group-config-new"},
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_permissions_another_object_role_retrieve_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=self.service_2, role_name="Service Action: action_1_service_2"
        ):
            with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
                response = self.client.v2[self.service_2, CONFIG_GROUPS].post(data={})
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_another_object_role_create_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=self.service_2, role_name="Service Action: action_1_service_2"
        ):
            with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
                response = self.client.v2[self.service_2, CONFIG_GROUPS].post(data={})
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_another_object_role_list_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=self.service_2, role_name="Service Action: action_1_service_2"
        ):
            with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
                response = self.client.v2[self.service_2, CONFIG_GROUPS].get()

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)


class TestComponentGroupConfig(BaseServiceGroupConfigTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.component_1_group_config = GroupConfig.objects.create(
            name="component_1_group_config",
            object_type=ContentType.objects.get_for_model(self.component_1),
            object_id=self.component_1.pk,
        )
        self.component_2_group_config = GroupConfig.objects.create(
            name="component_2_group_config",
            object_type=ContentType.objects.get_for_model(self.component_2),
            object_id=self.component_2.pk,
        )

        self.host_for_component = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_for_component"
        )
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_for_component)
        self.set_hostcomponent(
            cluster=self.cluster_1, entries=[(self.host, self.component_1), (self.host_for_component, self.component_1)]
        )
        self.component_1_group_config.hosts.add(self.host)

    def test_list_success(self):
        response = self.client.v2[self.component_1, CONFIG_GROUPS].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.component_1_group_config.pk)

    def test_retrieve_success(self):
        response = self.client.v2[self.component_1_group_config].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.component_1_group_config.pk)

    def test_create_success(self):
        response = self.client.v2[self.component_1, CONFIG_GROUPS].post(
            data={"name": "component-group-config-new", "description": "component-group-config-new"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()["name"], "component-group-config-new")

    def test_adcm_5285_create_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
            response = self.client.v2[self.component_1, CONFIG_GROUPS].post(
                data={"name": "component-group-config-new", "description": "component-group-config-new"},
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(response.json()["name"], "component-group-config-new")

    def test_create_no_permissions_fail(self):
        initial_group_config_ids = set(GroupConfig.objects.values_list("id", flat=True))

        user_password = "user_password"
        user_with_view_rights = self.create_user(username="user_with_view_rights", password=user_password)
        with self.grant_permissions(
            to=user_with_view_rights, on=self.component_1, role_name="View component configurations"
        ):
            self.client.login(username=user_with_view_rights.username, password=user_password)

            response = self.client.v2[self.component_1_group_config].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.v2[self.component_1, CONFIG_GROUPS].post(
                data={"name": "group-config-new", "description": "group-config-new"},
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertSetEqual(initial_group_config_ids, set(GroupConfig.objects.values_list("id", flat=True)))

    def test_adcm_5285_edit_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
            response = self.client.v2[self.component_1, CONFIG_GROUPS].post(
                data={"name": "component-group-config-new", "description": "component-group-config-new"},
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            group_config = GroupConfig.objects.get(pk=response.json()["id"])

            new_config = {
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

            response = self.client.v2[group_config, "configs"].post(data=new_config)

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(response.json()["description"], "new config")

    def test_delete_success(self):
        response = self.client.v2[self.component_1_group_config].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response = self.client.v2[self.component_1_group_config].get()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_adcm_5285_delete_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="Service Administrator"):
            response = self.client.v2[self.component_1_group_config].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

            response = self.client.v2[self.component_1_group_config].get()
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_list_hosts(self):
        response = self.client.v2[self.component_1_group_config, "hosts"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], self.host.name)

    def test_add_host_group_config_not_found_fail(self):
        non_existing_id = self.component_1_group_config.pk + 1000
        response = self.client.v2[self.component_1, CONFIG_GROUPS, non_existing_id, "hosts"].post(
            data={"hostId": self.host_for_component.pk},
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_add_host_success(self):
        response = self.client.v2[self.component_1_group_config, "hosts"].post(
            data={"hostId": self.host_for_component.pk}
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertDictEqual(
            d1=response.json(), d2={"id": self.host_for_component.pk, "name": self.host_for_component.name}
        )

    def test_list_host_candidates_success(self):
        response = self.client.v2[self.component_1_group_config, "host-candidates"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], self.host_for_component.name)

    def test_delete_host_success(self):
        response = self.client.v2[self.component_1_group_config, "hosts", self.host].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(self.host, Host.objects.get(id=self.host.pk))
        self.assertIn(self.host, self.cluster_1_group_config.hosts.all())
        self.assertIn(self.host, self.service_1_group_config.hosts.all())
        self.assertNotIn(self.host, self.component_1_group_config.hosts.all())

    def test_adcm_5199_config_description_inheritance(self):
        config_data = {
            "config": {
                "group": {"file": "new_content"},
                "activatable_group": {"secretfile": "new_content"},
                "secrettext": "new_secrettext",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "New description",
        }

        response = self.client.v2[self.component_1, CONFIG_GROUPS].post(
            data={"name": "Test group config", "description": ""}
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        group_config = GroupConfig.objects.get(pk=response.json()["id"])
        self.assertEqual(ConfigLog.objects.get(pk=group_config.config.current).description, "init")

        response = self.client.v2[self.component_1, "configs"].post(data=config_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        group_config.refresh_from_db()
        self.assertEqual(ConfigLog.objects.get(pk=group_config.config.current).description, config_data["description"])

    def test_permissions_another_model_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object configuration"):
            response = self.client.v2[self.component_1, CONFIG_GROUPS].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_permissions_another_object_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Cluster Administrator"):
            response = self.client.v2[self.component_1, CONFIG_GROUPS].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_permissions_another_object_role_create_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=self.component_2, role_name="Component Action: action_1_comp_2"
        ):
            with self.grant_permissions(
                to=self.test_user, on=self.component_1, role_name="View component configurations"
            ):
                response = self.client.v2[self.component_2, CONFIG_GROUPS].post(data={})
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_another_object_role_retrieve_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=self.component_2, role_name="Component Action: action_1_comp_2"
        ):
            with self.grant_permissions(
                to=self.test_user, on=self.component_1, role_name="View component configurations"
            ):
                response = self.client.v2[self.component_2_group_config].get()
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_another_object_role_list_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(
            to=self.test_user, on=self.component_2, role_name="Component Action: action_1_comp_2"
        ):
            with self.grant_permissions(
                to=self.test_user, on=self.component_1, role_name="View component configurations"
            ):
                response = self.client.v2[self.component_2, CONFIG_GROUPS].get()

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_adcm_5967_move_host_in_context_of_one_service(self):
        self.assertEqual(self.component_1_group_config.hosts.count(), 1)
        self.assertEqual(self.service_1_group_config.hosts.count(), 1)

        self.set_hostcomponent(
            cluster=self.cluster_1, entries=[(self.host_for_component, self.component_1), (self.host, self.component_2)]
        )

        self.assertEqual(self.component_1_group_config.hosts.count(), 0)
        self.assertEqual(self.service_1_group_config.hosts.count(), 1)
        self.assertListEqual(list(self.service_1_group_config.hosts.all()), [self.host])

    def test_adcm_5967_remove_host_from_service(self):
        self.assertEqual(self.component_1_group_config.hosts.count(), 1)
        self.assertEqual(self.service_1_group_config.hosts.count(), 1)

        self.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[(self.host_for_component, self.component_1), (self.host_for_component, self.component_2)],
        )

        self.assertEqual(self.component_1_group_config.hosts.count(), 0)
        self.assertEqual(self.service_1_group_config.hosts.count(), 0)


class TestHostProviderGroupConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host")
        self.new_host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="new-host")
        self.group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.provider),
            object_id=self.provider.pk,
        )
        self.group_config.hosts.add(self.host)
        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def test_list_success(self):
        response = self.client.v2[self.provider, CONFIG_GROUPS].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"],
            [{"description": "", "hosts": [{"id": 1, "name": "host"}], "id": 1, "name": "group_config"}],
        )

    def test_retrieve_success(self):
        response = self.client.v2[self.group_config].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(
            response.json(), {"description": "", "hosts": [{"id": 1, "name": "host"}], "id": 1, "name": "group_config"}
        )

    def test_create_success(self):
        response = self.client.v2[self.provider, CONFIG_GROUPS].post(
            data={"name": "group-config-new", "description": "group config new"}
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertDictEqual(
            response.json(), {"description": "group config new", "hosts": [], "id": 2, "name": "group-config-new"}
        )

    def test_create_without_config_fail(self):
        provider_no_config_bundle_path = self.test_bundles_dir / "provider_no_config"
        provider_no_config_bundle = self.add_bundle(source_dir=provider_no_config_bundle_path)
        provider_no_config = self.add_provider(bundle=provider_no_config_bundle, name="provider_no_config")

        initial_group_configs_count = GroupConfig.objects.count()

        response = self.client.v2[provider_no_config, CONFIG_GROUPS].post(
            data={"name": "group-config-new", "description": "group config new"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(GroupConfig.objects.count(), initial_group_configs_count)

    def test_create_no_permissions_fail(self):
        initial_group_config_ids = set(GroupConfig.objects.values_list("id", flat=True))

        user_password = "user_password"
        user_with_view_rights = self.create_user(username="user_with_view_rights", password=user_password)
        with self.grant_permissions(
            to=user_with_view_rights, on=self.provider, role_name="View provider configurations"
        ):
            self.client.login(username=user_with_view_rights.username, password=user_password)

            response = self.client.v2[self.group_config].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.v2[self.provider, CONFIG_GROUPS].post(
                data={"name": "group-config-new", "description": "group-config-new"},
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertSetEqual(initial_group_config_ids, set(GroupConfig.objects.values_list("id", flat=True)))

    def test_delete_success(self):
        response = self.client.v2[self.group_config].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_list_hosts_success(self):
        response = self.client.v2[self.group_config, "hosts"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(response.json(), [{"id": 1, "name": "host"}])

    def test_add_host_success(self):
        response = self.client.v2[self.group_config, "hosts"].post(data={"hostId": self.new_host.pk})

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertDictEqual(response.json(), {"id": 2, "name": "new-host"})

    def test_add_self_host_fail(self):
        response = self.client.v2[self.group_config, "hosts"].post(data={"hostId": self.host.pk})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "GROUP_CONFIG_HOST_EXISTS",
                "desc": "the host is already a member of this group ",
                "level": "error",
            },
        )

    def test_host_candidates(self):
        response = self.client.v2[self.group_config, "host-candidates"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(response.json(), [{"id": 2, "name": "new-host"}])

    def test_delete_host_success(self):
        response = self.client.v2[self.group_config, "hosts", self.host].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertNotIn(self.host, self.group_config.hosts.all())

    def test_adcm_5199_config_description_inheritance(self):
        config_data = {
            "config": {
                "group": {"map": {"integer_key": "99", "string_key": "new_string"}},
                "activatable_group": {
                    "secretmap": {
                        "integer_key": "101",
                        "string_key": "new-string",
                    }
                },
                "json": '{"key": "value", "new key": "new value"}',
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "brand new config",
        }

        response = self.client.v2[self.provider, CONFIG_GROUPS].post(
            data={"name": "Test group config", "description": ""}
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        group_config = GroupConfig.objects.get(pk=response.json()["id"])
        self.assertEqual(ConfigLog.objects.get(pk=group_config.config.current).description, "init")

        response = self.client.v2[self.provider, "configs"].post(data=config_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        group_config.refresh_from_db()
        self.assertEqual(ConfigLog.objects.get(pk=group_config.config.current).description, config_data["description"])

    def test_permissions_another_model_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object configuration"):
            response = self.client.v2[self.provider, CONFIG_GROUPS].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_permissions_another_object_role_list_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.provider, role_name="Provider Administrator"):
            response = self.client.v2[self.provider, CONFIG_GROUPS].get()
            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_permissions_another_object_role_create_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.provider, role_name="Provider Administrator"):
            response = self.client.v2[self.group_config, "hosts"].post(data={"hostId": self.new_host.pk})

            self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_permissions_provider_another_object_role_create_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.provider, role_name="Provider Action: provider_action"):
            with self.grant_permissions(to=self.test_user, on=self.host, role_name="Manage Maintenance mode"):
                response = self.client.v2[self.group_config].get()
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_provider_another_object_role_retrieve_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.provider, role_name="Provider Action: provider_action"):
            with self.grant_permissions(to=self.test_user, on=self.host, role_name="Manage Maintenance mode"):
                response = self.client.v2[self.group_config].get()
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_provider_another_object_role_list_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.provider, role_name="Provider Action: provider_action"):
            with self.grant_permissions(to=self.test_user, on=self.host, role_name="Manage Maintenance mode"):
                response = self.client.v2[self.provider, CONFIG_GROUPS].get()

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_cluster_another_object_role_create_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Map hosts"):
            with self.grant_permissions(to=self.test_user, on=self.host, role_name="Manage Maintenance mode"):
                response = self.client.v2[self.cluster_1, CONFIG_GROUPS].post(data={})
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_cluster_another_object_role_retrieve_denied(self):
        group = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.cluster_1),
            object_id=self.cluster_1.pk,
        )
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Map hosts"):
            with self.grant_permissions(to=self.test_user, on=self.host, role_name="Manage Maintenance mode"):
                response = self.client.v2[group].get()
                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_permissions_cluster_another_object_role_list_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Map hosts"):
            response = self.client.v2[self.cluster_1, CONFIG_GROUPS].get()

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)


class TestHostCandidateForConfigHostsGroups(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster = self.cluster_1
        self.service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1 = self.service.servicecomponent_set.get(prototype__name="component_1")
        self.component_2 = self.service.servicecomponent_set.get(prototype__name="component_2")

        self.hostprovider = self.provider
        self.hosts = tuple(self.add_host(provider=self.hostprovider, fqdn=f"host-{i}") for i in range(4))

    class Case(NamedTuple):
        target: ObjectWithConfigHostGroup
        # hosts to group
        add_to_first: tuple[Host, ...]
        add_to_second: tuple[Host, ...]
        # candidates
        at_start: tuple[Host, ...]
        after_one_added: tuple[Host, ...]
        after_second_added: tuple[Host, ...]

    @staticmethod
    def extract_ids(source: Response | Iterable[WithID]) -> list[int]:
        if isinstance(source, Response):
            data = source.json()
            getter = itemgetter
        else:
            data = source
            getter = attrgetter

        return list(map(getter("id"), data))

    def create_group_and_add_hosts_via_api(
        self, object_: ObjectWithConfigHostGroup, name: str, hosts: Iterable[Host]
    ) -> GroupConfig:
        response = self.client.v2[object_, CONFIG_GROUPS].post(data={"name": name, "description": ""})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        group_id = response.json()["id"]

        for host in hosts:
            self.assertEqual(
                self.client.v2[object_, CONFIG_GROUPS, group_id, "hosts"].post(data={"hostId": host.id}).status_code,
                HTTP_201_CREATED,
            )

        return GroupConfig.objects.get(id=group_id)

    def check_host_candidates_of_object(self, object_: ObjectWithConfigHostGroup, hosts: Iterable[Host]) -> None:
        response = self.client.v2[object_, CONFIG_GROUPS, HOST_CANDIDATES].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.extract_ids(response), self.extract_ids(hosts))

    def check_host_candidates_of_group(self, group: GroupConfig, hosts: Iterable[Host]) -> None:
        response = self.client.v2[group, HOST_CANDIDATES].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.extract_ids(response), self.extract_ids(hosts))

    def test_host_candidates(self) -> None:
        # prepare
        host_1, host_2, host_3, host_4 = self.hosts
        for host in self.hosts:
            self.add_host_to_cluster(cluster=self.cluster, host=host)
        self.set_hostcomponent(
            cluster=self.cluster,
            entries=[
                (host_1, self.component_1),
                (host_2, self.component_1),
                (host_3, self.component_1),
                (host_2, self.component_2),
                (host_4, self.component_2),
            ],
        )

        # cases
        cases = (
            self.Case(
                target=self.cluster,
                at_start=self.hosts,
                add_to_first=(host_1,),
                after_one_added=(host_2, host_3, host_4),
                add_to_second=(host_2, host_3),
                after_second_added=(host_4,),
            ),
            self.Case(
                target=self.service,
                at_start=self.hosts,
                add_to_first=(host_2, host_4),
                after_one_added=(host_1, host_3),
                add_to_second=(host_1, host_3),
                after_second_added=(),
            ),
            self.Case(
                target=self.component_1,
                at_start=(host_1, host_2, host_3),
                add_to_first=(),
                after_one_added=(host_1, host_2, host_3),
                add_to_second=(host_2,),
                after_second_added=(host_1, host_3),
            ),
            self.Case(
                target=self.hostprovider,
                at_start=self.hosts,
                add_to_first=(host_1, host_3, host_4),
                after_one_added=(host_2,),
                add_to_second=(),
                after_second_added=(host_2,),
            ),
        )

        # test
        for case in cases:
            target_desc = orm_object_to_core_type(case.target).name
            with self.subTest(f"[{target_desc}] No Groups"):
                self.check_host_candidates_of_object(object_=case.target, hosts=case.at_start)

            group_1 = self.create_group_and_add_hosts_via_api(
                object_=case.target, name=f"{target_desc} 1", hosts=case.add_to_first
            )

            with self.subTest(
                f"[{target_desc}] One Group | {len(case.add_to_first)} Hosts | {len(case.after_one_added)} Candidates"
            ):
                self.check_host_candidates_of_object(object_=case.target, hosts=case.after_one_added)
                self.check_host_candidates_of_group(group=group_1, hosts=case.after_one_added)

            group_2 = self.create_group_and_add_hosts_via_api(
                object_=case.target, name=f"{target_desc} 2", hosts=case.add_to_second
            )

            with self.subTest(
                f"[{target_desc}] One Group | {len(case.add_to_first)} Hosts | {len(case.after_one_added)} Candidates"
            ):
                self.check_host_candidates_of_object(object_=case.target, hosts=case.after_second_added)
                self.check_host_candidates_of_group(group=group_1, hosts=case.after_second_added)
                self.check_host_candidates_of_group(group=group_2, hosts=case.after_second_added)
