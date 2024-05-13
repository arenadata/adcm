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
import json

from cm.adcm_config.ansible import ansible_decrypt, ansible_encrypt_and_format
from cm.models import (
    ADCM,
    Action,
    Cluster,
    ClusterObject,
    ConcernItem,
    ConfigLog,
    GroupConfig,
    Host,
    HostProvider,
    ServiceComponent,
    Upgrade,
)
from cm.tests.mocks.task_runner import RunTaskMock
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.config.utils import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta
from api_v2.tests.base import BaseAPITestCase


class TestClusterConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_1_config = ConfigLog.objects.get(id=self.cluster_1.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_config.pk},
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = {
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "config": {
                "activatable_group": {"integer": 10},
                "boolean": True,
                "group": {"float": 0.1},
                "list": ["value1", "value2", "value3"],
                "variant_not_strict": "value1",
            },
            "creationTime": self.cluster_1_config.date.isoformat().replace("+00:00", "Z"),
            "description": "init",
            "id": self.cluster_1_config.pk,
            "isCurrent": True,
        }
        self.assertDictEqual(response.json(), data)

    def test_create_success(self):
        data = {
            "config": {
                "activatable_group": {"integer": 100},
                "boolean": False,
                "group": {"float": 2.1},
                "list": ["value1", "value2", "value3", "value4"],
                "variant_not_strict": "value5",
            },
            "adcmMeta": {"/activatable_group": {"isActive": False}},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}), data=data
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        response_data = response.json()
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_create_bad_attr_fail(self):
        data = {
            "config": {
                "activatable_group": {"integer": 100},
                "boolean": False,
                "group": {"float": 2.1},
                "list": ["value1", "value2", "value3", "value4"],
                "map_not_required": {"key": "value"},
                "variant_not_strict": "value5",
            },
            "adcmMeta": {"bad_key": "bad_value"},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}), data=data
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "ATTRIBUTE_ERROR",
                "desc": 'there isn\'t `bad_key` group in the config (cluster "cluster_one" 1.0)',
                "level": "error",
            },
        )

    def test_create_bad_and_good_attr_fail(self):
        data = {
            "config": {
                "activatable_group": {"integer": 100},
                "boolean": False,
                "group": {"float": 2.1},
                "list": ["value1", "value2", "value3", "value4"],
                "map_not_required": {"key": "value"},
                "variant_not_strict": "value5",
            },
            "adcmMeta": {"/activatable_group": {"isActive": False}, "/bad_key": {"isActive": False}},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}), data=data
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "ATTRIBUTE_ERROR",
                "desc": 'there isn\'t `bad_key` group in the config (cluster "cluster_one" 1.0)',
                "level": "error",
            },
        )

    def test_schema(self):
        response = self.client.get(path=reverse(viewname="v2:cluster-config-schema", kwargs={"pk": self.cluster_1.pk}))

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_cluster.json").read_text(encoding="utf-8")
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(response.json(), expected_data)


class TestSaveConfigWithoutRequiredField(BaseAPITestCase):
    """ADCM-4328"""

    def setUp(self) -> None:
        super().setUp()

        self.service = self.add_services_to_cluster(
            service_names=["service_4_save_config_without_required_field"], cluster=self.cluster_1
        ).get()

    def test_save_empty_config_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service.pk},
            ),
            data={"config": {}, "adcmMeta": {}},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.service.refresh_from_db()
        current_config = ConfigLog.objects.get(obj_ref=self.service.config, id=self.service.config.current).config

        self.assertDictEqual(current_config, {})

    def test_save_config_without_not_required_map_in_group_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service.pk},
            ),
            data={
                "config": {
                    "map_not_required": {"key": "value"},
                    "variant_not_required": "value1",
                    "group": {"variant_not_required": "value"},
                },
                "adcmMeta": {},
            },
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_default_raw_config_success(self):
        default_config_without_secrets = ConfigLog.objects.get(
            obj_ref=self.service.config, id=self.service.config.current
        ).config
        self.assertDictEqual(
            default_config_without_secrets,
            {
                "group": {"map_not_required": None, "variant_not_required": None},
                "map_not_required": None,
                "variant_not_required": None,
                "list": ["value1", "value2"],
            },
        )


class TestClusterGroupConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.cluster_1),
            object_id=self.cluster_1.pk,
        )
        self.group_config_config = ConfigLog.objects.get(pk=self.group_config.config.current)

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.group_config.pk},
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-group-config-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "group_config_pk": self.group_config.pk,
                    "pk": self.group_config_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = {
            "id": self.group_config_config.pk,
            "isCurrent": True,
            "creationTime": self.group_config_config.date.isoformat().replace("+00:00", "Z"),
            "config": {
                "activatable_group": {"integer": 10},
                "boolean": True,
                "group": {"float": 0.1},
                "list": ["value1", "value2", "value3"],
                "variant_not_strict": "value1",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/boolean": {"isSynchronized": True},
                "/group/float": {"isSynchronized": True},
                "/variant_not_strict": {"isSynchronized": True},
                "/list": {"isSynchronized": True},
                "/activatable_group/integer": {"isSynchronized": True},
            },
            "description": "init",
        }
        self.assertDictEqual(response.json(), data)

    def test_create_success(self):
        data = {
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

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.group_config.pk},
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_adcm_5219_create_non_superuser_privileged_success(self):
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Cluster Administrator"):
            data = {
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

            response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-group-config-config-list",
                    kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.group_config.pk},
                ),
                data=data,
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_create_no_permissions_fail(self):
        data = {
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
        initial_configlog_ids = set(ConfigLog.objects.values_list("id", flat=True))

        user_password = "user_password"
        user_with_view_rights = self.create_user(username="user_with_view_rights", password=user_password)
        with self.grant_permissions(
            to=user_with_view_rights, on=self.cluster_1, role_name="View cluster configurations"
        ):
            self.client.login(username=user_with_view_rights.username, password=user_password)

            response = self.client.get(
                path=reverse(
                    viewname="v2:cluster-group-config-config-detail",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "group_config_pk": self.group_config.pk,
                        "pk": self.group_config_config.pk,
                    },
                )
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-group-config-config-list",
                    kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.group_config.pk},
                ),
                data=data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertSetEqual(initial_configlog_ids, set(ConfigLog.objects.values_list("id", flat=True)))

    def test_cancel_sync(self):
        config = {
            "activatable_group": {"integer": 100},
            "boolean": False,
            "group": {"float": 2.1},
            "list": ["value1", "value2", "value3", "value4"],
            "variant_not_strict": "value5",
        }

        self.group_config_config.config = config
        self.group_config_config.attr.update(
            {
                "group_keys": {
                    "activatable_group": {"fields": {"integer": True}, "value": True},
                    "boolean": True,
                    "group": {"fields": {"float": True}, "value": None},
                    "list": True,
                    "variant_not_strict": True,
                }
            }
        )

        self.group_config_config.save(update_fields=["config", "attr"])

        data = {
            "config": config,
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/boolean": {"isSynchronized": False},
                "/group/float": {"isSynchronized": False},
                "/variant_not_strict": {"isSynchronized": True},
                "/list": {"isSynchronized": True},
                "/activatable_group/integer": {"isSynchronized": True},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.group_config.pk},
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        data["config"].update(
            {
                "activatable_group": {"integer": 10},
                "boolean": False,
                "group": {"float": 2.1},
                "list": ["value1", "value2", "value3"],
                "variant_not_strict": "value1",
            }
        )
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_primary_config_update(self):
        data = {
            "config": {
                "activatable_group": {"integer": 100},
                "boolean": False,
                "group": {"float": 1.1},
                "list": ["value1", "value2", "value3", "value4"],
                "variant_not_strict": "value5",
            },
            "adcmMeta": {"/activatable_group": {"isActive": False}},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}), data=data
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.group_config.refresh_from_db()
        config_log = ConfigLog.objects.get(id=self.group_config.config.current)

        self.assertDictEqual(config_log.config, data["config"])
        self.assertFalse(config_log.attr["activatable_group"]["active"])

    def test_adcm_4894_duplicate_name_fail(self):
        self.client.post(
            path=reverse(viewname="v2:cluster-group-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        response = self.client.post(
            path=reverse(viewname="v2:cluster-group-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BAD_REQUEST",
                "desc": f"name - Group config with name group-config-new "
                f"already exists for cm | cluster {self.cluster_1.name};",
                "level": "error",
            },
        )

    def test_create_bad_attr_fail(self):
        data = {
            "config": {
                "activatable_group": {"integer": 100},
                "boolean": False,
                "group": {"float": 2.1},
                "list": ["value1", "value2", "value3", "value4"],
                "variant_not_strict": "value5",
            },
            "adcmMeta": {
                "bad_key": "bad_value",
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.group_config.pk},
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "ATTRIBUTE_ERROR",
                "desc": 'there isn\'t `bad_key` group in the config (cluster "cluster_one" 1.0)',
                "level": "error",
            },
        )

    def test_create_bad_and_good_fail(self):
        data = {
            "config": {
                "activatable_group": {"integer": 100},
                "boolean": False,
                "group": {"float": 2.1},
                "list": ["value1", "value2", "value3", "value4"],
                "variant_not_strict": "value5",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/boolean": {"isSynchronized": True},
                "/group/float": {"isSynchronized": True},
                "/variant_not_strict": {"isSynchronized": True},
                "/list": {"isSynchronized": True},
                "/activatable_group/integer": {"isSynchronized": True},
                "/stringBAD": {"isSynchronized": False},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.group_config.pk},
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"code": "ATTRIBUTE_ERROR", "desc": "invalid `stringBAD/` field in `group_keys`", "level": "error"},
        )

    def test_schema(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-group-config-config-schema",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.group_config.pk},
            )
        )

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_cluster_group_config.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(response.json(), expected_data)


class TestServiceConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.service_1_initial_config = ConfigLog.objects.get(pk=self.service_1.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.service_1_initial_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = {
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "config": {
                "group": {"password": "password"},
                "activatable_group": {"text": "text"},
                "string": "string",
            },
            "creationTime": self.service_1_initial_config.date.isoformat().replace("+00:00", "Z"),
            "description": "init",
            "id": self.service_1_initial_config.pk,
            "isCurrent": True,
        }

        actual_data = response.json()
        actual_data["config"]["group"]["password"] = ansible_decrypt(msg=actual_data["config"]["group"]["password"])
        self.assertDictEqual(actual_data, expected_data)

    def test_create_success(self):
        data = {
            "config": {
                "group": {"password": "newpassword"},
                "activatable_group": {"text": "new text"},
                "string": "new string",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(
                viewname="v2:service-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        response_data["config"]["group"]["password"] = ansible_decrypt(msg=response_data["config"]["group"]["password"])

        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_schema(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-config-schema", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_1.pk}
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_service.json").read_text(encoding="utf-8")
        )
        actual_data = response.json()
        actual_data["properties"]["group"]["properties"]["password"]["default"] = ansible_decrypt(
            msg=actual_data["properties"]["group"]["properties"]["password"]["default"]
        )
        self.assertDictEqual(actual_data, expected_data)


class TestServiceGroupConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()

        self.group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.service_1),
            object_id=self.service_1.pk,
        )
        self.group_config_config = ConfigLog.objects.get(pk=self.group_config.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-group-config-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.group_config.pk,
                    "pk": self.group_config_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        expected_data = {
            "id": self.group_config_config.pk,
            "isCurrent": True,
            "creationTime": self.group_config_config.date.isoformat().replace("+00:00", "Z"),
            "config": {
                "group": {"password": "password"},
                "activatable_group": {"text": "text"},
                "string": "string",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/activatable_group/text": {"isSynchronized": True},
                "/group/password": {"isSynchronized": True},
                "/string": {"isSynchronized": True},
            },
            "description": "init",
        }
        actual_data = response.json()
        actual_data["config"]["group"]["password"] = ansible_decrypt(msg=actual_data["config"]["group"]["password"])
        self.assertDictEqual(actual_data, expected_data)

    def test_create_success(self):
        data = {
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

        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        response_data["config"]["group"]["password"] = ansible_decrypt(msg=response_data["config"]["group"]["password"])

        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_create_no_permissions_fail(self):
        data = {
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
        initial_configlog_ids = set(ConfigLog.objects.values_list("id", flat=True))

        user_password = "user_password"
        user_with_view_rights = self.create_user(username="user_with_view_rights", password=user_password)
        with self.grant_permissions(
            to=user_with_view_rights, on=self.service_1, role_name="View service configurations"
        ):
            self.client.login(username=user_with_view_rights.username, password=user_password)

            response = self.client.get(
                path=reverse(
                    viewname="v2:service-group-config-config-detail",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "group_config_pk": self.group_config.pk,
                        "pk": self.group_config_config.pk,
                    },
                )
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.post(
                path=reverse(
                    viewname="v2:service-group-config-config-list",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "group_config_pk": self.group_config.pk,
                    },
                ),
                data=data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertSetEqual(initial_configlog_ids, set(ConfigLog.objects.values_list("id", flat=True)))

    def test_cancel_sync(self):
        config = {
            "group": {"password": ansible_encrypt_and_format(msg="newpassword")},
            "activatable_group": {"text": "new text"},
            "string": "new string",
        }

        self.group_config_config.config = config
        self.group_config_config.attr.update(
            {
                "activatable_group": {"active": False},
                "group_keys": {
                    "activatable_group": {"fields": {"text": True}, "value": True},
                    "group": {"fields": {"password": True}, "value": None},
                    "string": True,
                },
            }
        )

        self.group_config_config.save(update_fields=["config", "attr"])

        data = {
            "config": config,
            "adcmMeta": {
                "/activatable_group": {"isActive": False, "isSynchronized": False},
                "/activatable_group/text": {"isSynchronized": False},
                "/group/password": {"isSynchronized": True},
                "/string": {"isSynchronized": True},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        response_data["config"]["group"]["password"] = ansible_decrypt(msg=response_data["config"]["group"]["password"])

        data["config"].update(
            {
                "group": {"password": "password"},
                "activatable_group": {"text": "new text"},
                "string": "string",
            }
        )

        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_primary_config_update(self):
        data = {
            "config": {
                "group": {"password": "newpassword"},
                "activatable_group": {"text": "new text"},
                "string": "new string",
            },
            "adcmMeta": {"/activatable_group": {"isActive": False}},
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:service-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.group_config.refresh_from_db()
        config_log = ConfigLog.objects.get(id=self.group_config.config.current)
        config_log.config["group"]["password"] = ansible_decrypt(msg=config_log.config["group"]["password"])
        data["config"]["group"]["password"] = ansible_decrypt(msg=data["config"]["group"]["password"])

        self.assertDictEqual(config_log.config, data["config"])
        self.assertFalse(config_log.attr["activatable_group"]["active"])

    def test_create_bad_attr_fail(self):
        data = {
            "config": {
                "group": {"password": "newpassword"},
                "activatable_group": {"text": "new text"},
                "string": "new string",
            },
            "adcmMeta": {
                "bad_key": "bad_value",
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "ATTRIBUTE_ERROR",
                "desc": 'there isn\'t `bad_key` group in the config (service "service_1" 1.0)',
                "level": "error",
            },
        )

    def test_create_bad_and_good_fail(self):
        data = {
            "config": {
                "group": {"password": "newpassword"},
                "activatable_group": {"text": "new text"},
                "string": "new string",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/activatable_group/text": {"isSynchronized": True},
                "/group/password": {"isSynchronized": True},
                "/string": {"isSynchronized": True},
                "/stringBAD": {"isSynchronized": False},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"code": "ATTRIBUTE_ERROR", "desc": "invalid `stringBAD/` field in `group_keys`", "level": "error"},
        )

    def test_schema(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-group-config-config-schema",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.group_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_service_group_config.json").read_text(
                encoding="utf-8"
            )
        )

        actual_data = response.json()
        actual_data["properties"]["group"]["properties"]["password"]["default"] = ansible_decrypt(
            msg=actual_data["properties"]["group"]["properties"]["password"]["default"]
        )
        self.assertDictEqual(actual_data, expected_data)


class TestComponentConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )
        self.component_1_initial_config = ConfigLog.objects.get(pk=self.component_1.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:component-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:component-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.component_1_initial_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = {
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "config": {
                "group": {"file": "content"},
                "activatable_group": {"secretfile": "content"},
                "secrettext": "secrettext",
            },
            "creationTime": self.component_1_initial_config.date.isoformat().replace("+00:00", "Z"),
            "description": "init",
            "id": self.component_1_initial_config.pk,
            "isCurrent": True,
        }
        actual_data = response.json()
        actual_data["config"]["secrettext"] = ansible_decrypt(msg=actual_data["config"]["secrettext"])
        actual_data["config"]["activatable_group"]["secretfile"] = ansible_decrypt(
            msg=actual_data["config"]["activatable_group"]["secretfile"]
        )

        self.assertDictEqual(actual_data, expected_data)

    def test_create_success(self):
        data = {
            "config": {
                "group": {"file": "new content"},
                "activatable_group": {"secretfile": "new content"},
                "secrettext": "new secrettext",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(
                viewname="v2:component-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        response_data["config"]["secrettext"] = ansible_decrypt(msg=response_data["config"]["secrettext"])
        response_data["config"]["activatable_group"]["secretfile"] = ansible_decrypt(
            msg=response_data["config"]["activatable_group"]["secretfile"]
        )

        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_schema(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:component-config-schema",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk, "pk": self.component_1.pk},
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_component.json").read_text(encoding="utf-8")
        )
        actual_data = response.json()
        actual_data["properties"]["secrettext"]["default"] = ansible_decrypt(
            msg=actual_data["properties"]["secrettext"]["default"]
        )
        actual_data["properties"]["activatable_group"]["properties"]["secretfile"]["default"] = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretfile"]["default"]
        )
        self.assertDictEqual(actual_data, expected_data)


class TestComponentGroupConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )

        self.group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.component_1),
            object_id=self.component_1.pk,
        )
        self.group_config_config = ConfigLog.objects.get(pk=self.group_config.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:component-group-config-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.group_config.pk,
                    "pk": self.group_config_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        expected_data = {
            "id": self.group_config_config.pk,
            "isCurrent": True,
            "creationTime": self.group_config_config.date.isoformat().replace("+00:00", "Z"),
            "config": {
                "group": {"file": "content"},
                "activatable_group": {"secretfile": "content"},
                "secrettext": "secrettext",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/activatable_group/secretfile": {"isSynchronized": True},
                "/group/file": {"isSynchronized": True},
                "/secrettext": {"isSynchronized": True},
            },
            "description": "init",
        }
        actual_data = response.json()
        actual_data["config"]["secrettext"] = ansible_decrypt(msg=actual_data["config"]["secrettext"])
        actual_data["config"]["activatable_group"]["secretfile"] = ansible_decrypt(
            msg=actual_data["config"]["activatable_group"]["secretfile"]
        )
        self.assertDictEqual(actual_data, expected_data)

    def test_create_success(self):
        data = {
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

        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        response_data["config"]["secrettext"] = ansible_decrypt(msg=response_data["config"]["secrettext"])
        response_data["config"]["activatable_group"]["secretfile"] = ansible_decrypt(
            msg=response_data["config"]["activatable_group"]["secretfile"]
        )

        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_create_no_permissions_fail(self):
        data = {
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
        initial_configlog_ids = set(ConfigLog.objects.values_list("id", flat=True))

        user_password = "user_password"
        user_with_view_rights = self.create_user(username="user_with_view_rights", password=user_password)
        with self.grant_permissions(
            to=user_with_view_rights, on=self.component_1, role_name="View component configurations"
        ):
            self.client.login(username=user_with_view_rights.username, password=user_password)

            response = self.client.get(
                path=reverse(
                    viewname="v2:component-group-config-config-detail",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "component_pk": self.component_1.pk,
                        "group_config_pk": self.group_config.pk,
                        "pk": self.group_config_config.pk,
                    },
                )
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.post(
                path=reverse(
                    viewname="v2:component-group-config-config-list",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "component_pk": self.component_1.pk,
                        "group_config_pk": self.group_config.pk,
                    },
                ),
                data=data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertSetEqual(initial_configlog_ids, set(ConfigLog.objects.values_list("id", flat=True)))

    def test_cancel_sync(self):
        config = {
            "group": {"file": "new content"},
            "activatable_group": {"secretfile": "new content"},
            "secrettext": "new secrettext",
        }

        self.group_config_config.config = config
        self.group_config_config.attr.update(
            {
                "group_keys": {
                    "activatable_group": {"fields": {"secretfile": True}, "value": True},
                    "group": {"fields": {"file": True}, "value": None},
                    "secrettext": True,
                }
            }
        )

        self.group_config_config.save(update_fields=["config", "attr"])

        data = {
            "config": config,
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/activatable_group/secretfile": {"isSynchronized": True},
                "/group/file": {"isSynchronized": False},
                "/secrettext": {"isSynchronized": True},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        response_data["config"]["secrettext"] = ansible_decrypt(msg=response_data["config"]["secrettext"])
        response_data["config"]["activatable_group"]["secretfile"] = ansible_decrypt(
            msg=response_data["config"]["activatable_group"]["secretfile"]
        )

        data["config"].update(
            {
                "group": {"file": "new content"},
                "activatable_group": {"secretfile": "content"},
                "secrettext": "secrettext",
            }
        )

        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

        self.assertEqual(
            Path(
                settings.FILE_DIR / f"component.{self.component_1.pk}.group.{self.group_config.pk}.group.file"
            ).read_text(encoding="UTF-8"),
            "new content",
        )
        self.assertEqual(
            Path(
                settings.FILE_DIR
                / f"component.{self.component_1.pk}.group.{self.group_config.pk}.activatable_group.secretfile"
            ).read_text(encoding="UTF-8"),
            "content",
        )

    def test_primary_config_update(self):
        data = {
            "config": {
                "group": {"file": "new content"},
                "activatable_group": {"secretfile": "new content"},
                "secrettext": "new secrettext",
            },
            "adcmMeta": {"/activatable_group": {"isActive": False}},
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:component-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.group_config.refresh_from_db()
        config_log = ConfigLog.objects.get(id=self.group_config.config.current)
        config_log.config["activatable_group"]["secretfile"] = ansible_decrypt(
            msg=config_log.config["activatable_group"]["secretfile"]
        )
        config_log.config["secrettext"] = ansible_decrypt(msg=config_log.config["secrettext"])
        data["config"]["activatable_group"]["secretfile"] = ansible_decrypt(
            msg=data["config"]["activatable_group"]["secretfile"]
        )
        data["config"]["secrettext"] = ansible_decrypt(msg=data["config"]["secrettext"])

        self.assertDictEqual(config_log.config, data["config"])
        self.assertFalse(config_log.attr["activatable_group"]["active"])

        self.assertEqual(
            Path(
                settings.FILE_DIR / f"component.{self.component_1.pk}.group.{self.group_config.pk}.group.file"
            ).read_text(encoding="UTF-8"),
            "new content",
        )
        self.assertEqual(
            Path(
                settings.FILE_DIR
                / f"component.{self.component_1.pk}.group.{self.group_config.pk}.activatable_group.secretfile"
            ).read_text(encoding="UTF-8"),
            "new content",
        )

    def test_create_bad_attr_fail(self):
        data = {
            "config": {
                "group": {"file": "new content"},
                "activatable_group": {"secretfile": "new content"},
                "secrettext": "new secrettext",
            },
            "adcmMeta": {
                "bad_key": "bad_value",
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "ATTRIBUTE_ERROR",
                "desc": 'there isn\'t `bad_key` group in the config (component "component_1" 1.0)',
                "level": "error",
            },
        )

    def test_create_bad_and_good_fail(self):
        data = {
            "config": {
                "group": {"file": "new content"},
                "activatable_group": {"secretfile": "new content"},
                "secrettext": "new secrettext",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/activatable_group/secretfile": {"isSynchronized": True},
                "/group/file": {"isSynchronized": True},
                "/secrettext": {"isSynchronized": True},
                "/stringBAD": {"isSynchronized": False},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"code": "ATTRIBUTE_ERROR", "desc": "invalid `stringBAD/` field in `group_keys`", "level": "error"},
        )

    def test_schema(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:component-group-config-config-schema",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.group_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_component_group_config.json").read_text(
                encoding="utf-8"
            )
        )
        actual_data = response.json()
        actual_data["properties"]["activatable_group"]["properties"]["secretfile"]["default"] = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretfile"]["default"]
        )
        actual_data["properties"]["secrettext"]["default"] = ansible_decrypt(
            msg=actual_data["properties"]["secrettext"]["default"]
        )
        self.assertDictEqual(actual_data, expected_data)


class TestProviderConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.provider_initial_config = ConfigLog.objects.get(pk=self.provider.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:provider-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                },
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:provider-config-detail",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "pk": self.provider_initial_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = {
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "config": {
                "group": {"map": {"integer_key": "10", "string_key": "string"}},
                "activatable_group": {
                    "secretmap": {
                        "integer_key": "10",
                        "string_key": "string",
                    }
                },
                "json": '{"key": "value"}',
            },
            "creationTime": self.provider_initial_config.date.isoformat().replace("+00:00", "Z"),
            "description": "init",
            "id": self.provider_initial_config.pk,
            "isCurrent": True,
        }
        actual_data = response.json()
        actual_data["config"]["activatable_group"]["secretmap"]["integer_key"] = ansible_decrypt(
            msg=actual_data["config"]["activatable_group"]["secretmap"]["integer_key"]
        )
        actual_data["config"]["activatable_group"]["secretmap"]["string_key"] = ansible_decrypt(
            msg=actual_data["config"]["activatable_group"]["secretmap"]["string_key"]
        )
        self.assertDictEqual(actual_data, expected_data)

    def test_retrieve_wrong_pk_fail(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:provider-config-detail",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "pk": self.get_non_existent_pk(model=ConfigLog),
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_wrong_provider_pk_fail(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:provider-config-detail",
                kwargs={
                    "hostprovider_pk": self.get_non_existent_pk(model=HostProvider),
                    "pk": self.provider_initial_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_create_success(self):
        data = {
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
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(
                viewname="v2:provider-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                },
            ),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        response_data["config"]["activatable_group"]["secretmap"]["integer_key"] = ansible_decrypt(
            msg=response_data["config"]["activatable_group"]["secretmap"]["integer_key"]
        )
        response_data["config"]["activatable_group"]["secretmap"]["string_key"] = ansible_decrypt(
            msg=response_data["config"]["activatable_group"]["secretmap"]["string_key"]
        )
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_schema(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:hostprovider-config-schema",
                kwargs={"pk": self.provider.pk},
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_hostprovider.json").read_text(encoding="utf-8")
        )
        actual_data = response.json()

        integer_key = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["oneOf"][0]["default"][
                "integer_key"
            ]
        )
        actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["oneOf"][0]["default"][
            "integer_key"
        ] = integer_key
        string_key = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["oneOf"][0]["default"][
                "string_key"
            ]
        )
        actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["oneOf"][0]["default"][
            "string_key"
        ] = string_key

        self.assertDictEqual(actual_data, expected_data)


class TestProviderGroupConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.provider),
            object_id=self.provider.pk,
        )
        self.group_config_config = ConfigLog.objects.get(pk=self.group_config.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={"hostprovider_pk": self.provider.pk, "group_config_pk": self.group_config.pk},
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-detail",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "group_config_pk": self.group_config.pk,
                    "pk": self.group_config_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = {
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/json": {"isSynchronized": True},
                "/group/map": {"isSynchronized": True},
                "/activatable_group/secretmap": {"isSynchronized": True},
            },
            "config": {
                "group": {"map": {"integer_key": "10", "string_key": "string"}},
                "activatable_group": {
                    "secretmap": {
                        "integer_key": "10",
                        "string_key": "string",
                    }
                },
                "json": '{"key": "value"}',
            },
            "creationTime": self.group_config_config.date.isoformat().replace("+00:00", "Z"),
            "description": "init",
            "id": self.group_config_config.pk,
            "isCurrent": True,
        }
        actual_data = response.json()
        actual_data["config"]["activatable_group"]["secretmap"]["integer_key"] = ansible_decrypt(
            msg=actual_data["config"]["activatable_group"]["secretmap"]["integer_key"]
        )
        actual_data["config"]["activatable_group"]["secretmap"]["string_key"] = ansible_decrypt(
            msg=actual_data["config"]["activatable_group"]["secretmap"]["string_key"]
        )
        self.assertDictEqual(actual_data, expected_data)

    def test_retrieve_wrong_pk_fail(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-detail",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "group_config_pk": self.group_config.pk,
                    "pk": self.get_non_existent_pk(model=ConfigLog),
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_wrong_provider_pk_fail(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:provider-config-detail",
                kwargs={
                    "hostprovider_pk": self.get_non_existent_pk(model=HostProvider),
                    "pk": self.group_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_create_success(self):
        data = {
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
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        response_data["config"]["activatable_group"]["secretmap"]["integer_key"] = ansible_decrypt(
            msg=response_data["config"]["activatable_group"]["secretmap"]["integer_key"]
        )
        response_data["config"]["activatable_group"]["secretmap"]["string_key"] = ansible_decrypt(
            msg=response_data["config"]["activatable_group"]["secretmap"]["string_key"]
        )
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_create_no_permissions_fail(self):
        data = {
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
        initial_configlog_ids = set(ConfigLog.objects.values_list("id", flat=True))

        user_password = "user_password"
        user_with_view_rights = self.create_user(username="user_with_view_rights", password=user_password)
        with self.grant_permissions(
            to=user_with_view_rights, on=self.provider, role_name="View provider configurations"
        ):
            self.client.login(username=user_with_view_rights.username, password=user_password)

            response = self.client.get(
                path=reverse(
                    viewname="v2:hostprovider-group-config-config-detail",
                    kwargs={
                        "hostprovider_pk": self.provider.pk,
                        "group_config_pk": self.group_config.pk,
                        "pk": self.group_config_config.pk,
                    },
                )
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            response = self.client.post(
                path=reverse(
                    viewname="v2:hostprovider-group-config-config-list",
                    kwargs={
                        "hostprovider_pk": self.provider.pk,
                        "group_config_pk": self.group_config.pk,
                    },
                ),
                data=data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertSetEqual(initial_configlog_ids, set(ConfigLog.objects.values_list("id", flat=True)))

    def test_cancel_sync(self):
        config = {
            "group": {"map": {"integer_key": "100", "string_key": "new string"}},
            "activatable_group": {
                "secretmap": {
                    "integer_key": "100",
                    "string_key": "new string",
                }
            },
            "json": '{"key": "value", "new key": "new value"}',
        }

        self.group_config_config.config = config
        self.group_config_config.attr.update(
            {
                "group_keys": {
                    "activatable_group": {"fields": {"secretmap": True}, "value": True},
                    "group": {"fields": {"map": True}, "value": None},
                    "json": True,
                }
            }
        )

        self.group_config_config.save(update_fields=["config", "attr"])

        data = {
            "config": config,
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/activatable_group/secretmap": {"isSynchronized": True},
                "/group/map": {"isSynchronized": False},
                "/json": {"isSynchronized": True},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "group_config_pk": self.group_config.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()

        response_data["config"]["activatable_group"]["secretmap"]["integer_key"] = ansible_decrypt(
            msg=response_data["config"]["activatable_group"]["secretmap"]["integer_key"]
        )
        response_data["config"]["activatable_group"]["secretmap"]["string_key"] = ansible_decrypt(
            msg=response_data["config"]["activatable_group"]["secretmap"]["string_key"]
        )

        data["config"].update(
            {
                "group": {"map": {"integer_key": "100", "string_key": "new string"}},
                "activatable_group": {
                    "secretmap": {
                        "integer_key": "10",
                        "string_key": "string",
                    }
                },
                "json": '{"key": "value"}',
            }
        )

        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

    def test_primary_config_update(self):
        data = {
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
            "adcmMeta": {"/activatable_group": {"isActive": False}},
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:provider-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                },
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.group_config.refresh_from_db()
        config_log = ConfigLog.objects.get(id=self.group_config.config.current)
        config_log.config["activatable_group"]["secretmap"]["integer_key"] = ansible_decrypt(
            msg=config_log.config["activatable_group"]["secretmap"]["integer_key"]
        )
        config_log.config["activatable_group"]["secretmap"]["string_key"] = ansible_decrypt(
            msg=config_log.config["activatable_group"]["secretmap"]["string_key"]
        )

        data["config"]["activatable_group"]["secretmap"]["integer_key"] = ansible_decrypt(
            msg=data["config"]["activatable_group"]["secretmap"]["integer_key"]
        )
        data["config"]["activatable_group"]["secretmap"]["string_key"] = ansible_decrypt(
            msg=data["config"]["activatable_group"]["secretmap"]["string_key"]
        )

        data["config"]["json"] = json.loads(data["config"]["json"])

        self.assertDictEqual(config_log.config, data["config"])
        self.assertFalse(config_log.attr["activatable_group"]["active"])

    def test_schema(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-schema",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.group_config.pk},
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_hostprovider_group_config.json").read_text(
                encoding="utf-8"
            )
        )
        actual_data = response.json()

        integer_key = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["oneOf"][0]["default"][
                "integer_key"
            ]
        )
        actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["oneOf"][0]["default"][
            "integer_key"
        ] = integer_key
        string_key = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["oneOf"][0]["default"][
                "string_key"
            ]
        )
        actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["oneOf"][0]["default"][
            "string_key"
        ] = string_key

        self.assertDictEqual(actual_data, expected_data)


class TestHostConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.host_config = ConfigLog.objects.get(pk=self.host.config.current)

    def test_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.host.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:host-config-detail", kwargs={"host_pk": self.host.pk, "pk": self.host_config.pk})
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        data = {
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "config": {
                "activatable_group": {"option": "string1"},
                "group": {"list": ["value1", "value2", "value3"]},
                "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                "variant": "value1",
            },
            "creationTime": self.host_config.date.isoformat().replace("+00:00", "Z"),
            "description": "init",
            "id": self.host_config.pk,
            "isCurrent": True,
        }
        self.assertDictEqual(response.json(), data)

    def test_create_success(self):
        data = {
            "config": {
                "activatable_group": {"option": "string2"},
                "group": {"list": ["value1", "value2", "value3", "value4"]},
                "structure": [
                    {"integer": 1, "string": "string1"},
                    {"integer": 2, "string": "string2"},
                    {"integer": 3, "string": "string3"},
                ],
                "variant": "value2",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.host.pk}),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

        response = self.client.get(path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.host.pk}))
        self.assertEqual(response.json()["count"], 2)

    def test_list_wrong_pk_fail(self):
        response = self.client.get(
            path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.get_non_existent_pk(Host)})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_schema(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:host-config-schema",
                kwargs={"pk": self.host.pk},
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_host.json").read_text(encoding="utf-8")
        )
        actual_data = response.json()

        self.assertDictEqual(actual_data, expected_data)


class TestADCMConfig(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")
        self.adcm = ADCM.objects.first()
        self.adcm_current_config = ConfigLog.objects.get(id=self.adcm.config.current)

    def test_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:adcm-config-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertListEqual(
            sorted(data["results"][0].keys()), sorted(["id", "isCurrent", "creationTime", "description"])
        )
        self.assertTrue(data["results"][0]["isCurrent"])

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:adcm-config-detail", kwargs={"pk": self.adcm_current_config.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["isCurrent"])
        self.assertDictEqual(
            data["adcmMeta"],
            {
                "/logrotate": {"isActive": False},
                "/ldap_integration": {"isActive": False},
                "/statistics_collection": {"isActive": True},
            },
        )

    def test_create_success(self):
        data = {
            "config": {
                "global": {"adcm_url": "http://127.0.0.1:8000", "verification_public_key": "\n"},
                "google_oauth": {"client_id": None, "secret": None},
                "yandex_oauth": {"client_id": None, "secret": None},
                "ansible_settings": {"forks": 5},
                "logrotate": {"size": "10M", "max_history": 10, "compress": False},
                "audit_data_retention": {
                    "log_rotation_on_fs": 365,
                    "log_rotation_in_db": 365,
                    "config_rotation_in_db": 0,
                    "retention_period": 1825,
                    "data_archiving": False,
                },
                "ldap_integration": {
                    "ldap_uri": None,
                    "ldap_user": None,
                    "ldap_password": None,
                    "user_search_base": None,
                    "user_search_filter": None,
                    "user_object_class": "user",
                    "user_name_attribute": "sAMAccountName",
                    "group_search_base": None,
                    "group_search_filter": None,
                    "group_object_class": "group",
                    "group_name_attribute": "cn",
                    "group_member_attribute_name": "member",
                    "sync_interval": 60,
                    "tls_ca_cert_file": None,
                },
                "statistics_collection": {"url": "statistics_url"},
                "auth_policy": {
                    "min_password_length": 12,
                    "max_password_length": 20,
                    "login_attempt_limit": 5,
                    "block_time": 5,
                },
            },
            "adcmMeta": {
                "/logrotate": {"isActive": False},
                "/ldap_integration": {"isActive": False},
                "/statistics_collection": {"isActive": False},
            },
            "description": "new ADCM config",
        }

        response = self.client.post(path=reverse(viewname="v2:adcm-config-list"), data=data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(ConfigLog.objects.filter(obj_ref=self.adcm.config).count(), 2)
        self.assertTrue(response.json()["isCurrent"])
        self.assertEqual(response.json()["description"], "new ADCM config")

    def test_schema(self):
        response = self.client.get(path=reverse(viewname="v2:adcm-config-schema"))
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_adcm.json").read_text(encoding="utf-8")
        )
        actual_data = response.json()

        self.assertDictEqual(actual_data, expected_data)


class TestAttrTransformation(BaseAPITestCase):
    def test_transformation_success(self):
        attr = {
            "activatable_group": {"active": True},
            "group_keys": {
                "group": {"value": None, "fields": {"string": False}},
                "activatable_group": {
                    "value": True,
                    "fields": {"string": True},
                },
                "string": True,
            },
        }
        adcm_meta = convert_attr_to_adcm_meta(attr=attr)
        expected_adcm_meta = {
            "/activatable_group": {"isActive": True, "isSynchronized": False},
            "/activatable_group/string": {"isSynchronized": False},
            "/group/string": {"isSynchronized": True},
            "/string": {"isSynchronized": False},
        }

        self.assertDictEqual(adcm_meta, expected_adcm_meta)
        new_attr = convert_adcm_meta_to_attr(adcm_meta=adcm_meta)
        self.assertDictEqual(new_attr, attr)

    def test_incorrect_attr_to_adcm_meta_fail(self):
        attr = {
            "activatable_group": {"active": True},
            "group_keys": {
                "group": {"value": None, "fields": {"string": False}},
                "activatable_group": {
                    "bad_value": True,
                    "fields": {"string": True},
                },
                "string": True,
            },
        }
        with self.assertRaises(KeyError):
            convert_attr_to_adcm_meta(attr=attr)

    def test_adcm_meta_to_attr_returns_unchanged_on_fail(self):
        adcm_meta = {
            "/activatable_group": {"isActive": True, "isSynchronized": True},
            "/activatable_group/string": {"isSynchronized": True},
            "/group/string": {"isSynchronized": False},
            "/string": {},
        }

        new_attr = convert_adcm_meta_to_attr(adcm_meta=adcm_meta)
        self.assertDictEqual(new_attr, adcm_meta)


class TestConfigSchemaEnumWithoutValues(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service = self.add_services_to_cluster(
            service_names=["service_5_variant_type_without_values"], cluster=self.cluster_1
        ).get()

    def test_schema(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-config-schema", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service.pk}
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(
            response.json(),
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Configuration",
                "description": "",
                "readOnly": False,
                "adcmMeta": {
                    "isAdvanced": False,
                    "isInvisible": False,
                    "activation": None,
                    "synchronization": None,
                    "nullValue": None,
                    "isSecret": False,
                    "stringExtra": None,
                    "enumExtra": None,
                },
                "type": "object",
                "properties": {
                    "variant": {
                        "title": "variant",
                        "description": "",
                        "default": None,
                        "readOnly": False,
                        "adcmMeta": {
                            "isAdvanced": False,
                            "isInvisible": False,
                            "activation": None,
                            "synchronization": None,
                            "isSecret": False,
                            "stringExtra": {"isMultiline": False},
                            "enumExtra": None,
                        },
                        "enum": [None],
                    }
                },
                "additionalProperties": False,
                "required": ["variant"],
            },
        )


class TestGroupConfigUpgrade(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = self.test_bundles_dir / "cluster_group_config"
        cluster_bundle_2_path = self.test_bundles_dir / "cluster_group_config_upgrade"

        self.bundle_1 = self.add_bundle(source_dir=cluster_bundle_1_path)
        self.bundle_2 = self.add_bundle(source_dir=cluster_bundle_2_path)
        self.upgrade = Upgrade.objects.get(name="upgrade", bundle=self.bundle_2)

        self.cluster = self.add_cluster(bundle=self.bundle_1, name="cluster_group_config")
        self.service = self.add_services_to_cluster(service_names=["service"], cluster=self.cluster).get()
        self.component = ServiceComponent.objects.filter(cluster=self.cluster, service=self.service).first()

        self.cluster_group_config = GroupConfig.objects.create(
            name="cluster_group_config", object_type=self.cluster.content_type, object_id=self.cluster.pk
        )
        config = ConfigLog.objects.get(pk=self.cluster_group_config.config.current)
        config.config.update({"activatable_group": {"integer": 100}, "boolean": True, "group": {"float": 0.1}})
        config.attr.update(
            {
                "group_keys": {
                    "activatable_group": {"fields": {"integer": True}, "value": False},
                    "boolean": False,
                    "group": {"fields": {"float": False}, "value": None},
                }
            }
        )
        config.save(update_fields=["config", "attr"])

        self.service_group_config = GroupConfig.objects.create(
            name="service_group_config", object_type=self.service.content_type, object_id=self.service.pk
        )
        config = ConfigLog.objects.get(pk=self.service_group_config.config.current)
        config.config.update(
            {
                "group": {"password": ansible_encrypt_and_format(msg="new password")},
                "activatable_group": {"text": "text"},
                "string": "new string",
            }
        )
        config.attr.update(
            {
                "activatable_group": {"active": False},
                "group_keys": {
                    "activatable_group": {"fields": {"text": False}, "value": True},
                    "group": {"fields": {"password": True}, "value": None},
                    "string": True,
                },
            }
        )
        config.save(update_fields=["config", "attr"])

        self.component_group_config = GroupConfig.objects.create(
            name="component_group_config", object_type=self.component.content_type, object_id=self.component.pk
        )
        config = ConfigLog.objects.get(pk=self.component_group_config.config.current)
        config.config.update(
            {
                "group": {"file": "content"},
                "activatable_group": {"secretfile": ansible_encrypt_and_format(msg="new content")},
                "secrettext": ansible_encrypt_and_format(msg="secrettext"),
            }
        )
        config.attr.update(
            {
                "group_keys": {
                    "activatable_group": {"fields": {"secretfile": True}, "value": True},
                    "group": {"fields": {"file": False}, "value": None},
                    "secrettext": False,
                },
            }
        )
        config.save(update_fields=["config", "attr"])

    def test_upgrade(self):
        config_of_cluster_group = ConfigLog.objects.get(id=self.cluster_group_config.config.current)
        self.assertDictEqual(
            config_of_cluster_group.config,
            {"activatable_group": {"integer": 100}, "boolean": True, "group": {"float": 0.1}},
        )
        self.assertDictEqual(
            config_of_cluster_group.attr,
            {
                "activatable_group": {"active": True},
                "group_keys": {
                    "activatable_group": {"fields": {"integer": True}, "value": False},
                    "boolean": False,
                    "group": {"fields": {"float": False}, "value": None},
                },
                "custom_group_keys": {
                    "boolean": True,
                    "group": {"value": True, "fields": {"float": True}},
                    "activatable_group": {"value": True, "fields": {"integer": True}},
                },
            },
        )

        config_of_service_group = ConfigLog.objects.get(id=self.service_group_config.config.current)
        config_of_service_group.config["group"]["password"] = ansible_decrypt(
            msg=config_of_service_group.config["group"]["password"]
        )
        self.assertDictEqual(
            config_of_service_group.config,
            {
                "group": {"password": "new password"},
                "activatable_group": {"text": "text"},
                "string": "new string",
            },
        )
        self.assertDictEqual(
            config_of_service_group.attr,
            {
                "activatable_group": {"active": False},
                "group_keys": {
                    "activatable_group": {"fields": {"text": False}, "value": True},
                    "group": {"fields": {"password": True}, "value": None},
                    "string": True,
                },
                "custom_group_keys": {
                    "string": True,
                    "group": {"value": True, "fields": {"password": True}},
                    "activatable_group": {"value": True, "fields": {"text": True}},
                },
            },
        )

        config_of_component_group = ConfigLog.objects.get(id=self.component_group_config.config.current)
        config_of_component_group.config["activatable_group"]["secretfile"] = ansible_decrypt(
            msg=config_of_component_group.config["activatable_group"]["secretfile"]
        )
        config_of_component_group.config["secrettext"] = ansible_decrypt(
            msg=config_of_component_group.config["secrettext"]
        )
        self.assertDictEqual(
            config_of_component_group.config,
            {
                "group": {"file": "content"},
                "activatable_group": {"secretfile": "new content"},
                "secrettext": "secrettext",
            },
        )
        self.assertDictEqual(
            config_of_component_group.attr,
            {
                "activatable_group": {"active": True},
                "group_keys": {
                    "activatable_group": {"fields": {"secretfile": True}, "value": True},
                    "group": {"fields": {"file": False}, "value": None},
                    "secrettext": False,
                },
                "custom_group_keys": {
                    "secrettext": True,
                    "group": {"value": True, "fields": {"file": True}},
                    "activatable_group": {"value": True, "fields": {"secretfile": True}},
                },
            },
        )

        response = self.client.post(
            path=reverse(viewname="v2:upgrade-run", kwargs={"cluster_pk": self.cluster.pk, "pk": self.upgrade.pk})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.cluster_group_config.refresh_from_db()
        self.service_group_config.refresh_from_db()
        self.component_group_config.refresh_from_db()

        config_of_cluster_group = ConfigLog.objects.get(id=self.cluster_group_config.config.current)
        self.assertDictEqual(
            config_of_cluster_group.config,
            {"activatable_group": {"integer": 100}, "boolean": False, "json": {"key": "value"}},
        )
        self.assertDictEqual(
            config_of_cluster_group.attr,
            {
                "activatable_group": {"active": True},
                "group_keys": {
                    "boolean": False,
                    "json": False,
                    "activatable_group": {"value": False, "fields": {"integer": True}},
                },
                "custom_group_keys": {
                    "boolean": True,
                    "json": True,
                    "activatable_group": {"value": True, "fields": {"integer": True}},
                },
            },
        )

        config_of_service_group = ConfigLog.objects.get(id=self.service_group_config.config.current)
        self.assertDictEqual(
            config_of_service_group.config,
            {
                "group": {"map": {"integer_key": "10", "string_key": "string"}},
                "string": "new string",
                "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
            },
        )
        self.assertDictEqual(
            config_of_service_group.attr,
            {
                "custom_group_keys": {
                    "group": {"fields": {"map": True}, "value": True},
                    "string": True,
                    "structure": True,
                },
                "group_keys": {"group": {"fields": {"map": False}, "value": None}, "string": True, "structure": False},
            },
        )

        config_of_component_group = ConfigLog.objects.get(id=self.component_group_config.config.current)
        config_of_component_group.config["secrettext"] = ansible_decrypt(config_of_component_group.config["secrettext"])
        self.assertDictEqual(
            config_of_component_group.config,
            {
                "secrettext": "new secrettext",
                "group": {"file": "new content"},
                "activatable_group": {"option": "string1"},
            },
        )
        self.assertDictEqual(
            config_of_component_group.attr,
            {
                "activatable_group": {"active": True},
                "group_keys": {
                    "secrettext": False,
                    "group": {"value": None, "fields": {"file": False}},
                    "activatable_group": {"value": True, "fields": {"option": False}},
                },
                "custom_group_keys": {
                    "secrettext": True,
                    "group": {"value": True, "fields": {"file": True}},
                    "activatable_group": {"value": True, "fields": {"option": True}},
                },
            },
        )


class TestPatternInConfig(BaseAPITestCase):
    _PATTERNS = {
        "patterned_string": r"[a-z][A-Z][0-9]*?",
        "patterned_password": r"[A-z]{4,}[0-9]+[^A-z0-9]+",
        "patterned_text": r"^(entry: [a-z]{2,16}_[0-9]+\n){1,3}summary: (OK|FAIL) [0-9]+$",
        "patterned_secrettext": r"HEADER\s[A-z0-9]{8,}\n((OK(?=\s0+\n)|FAIL(?!\s0+\n))\s[0-9]+)+?\n",
        "patterned_string_exclude_dot": r"^[^\.]*$",
    }
    _EXAMPLES = {
        "ok": {
            "patterned_string": ["oX4", "eH", "aA0"],
            "patterned_password": ["Qwer8#", "oVEr3@"],
            "patterned_text": [
                "entry: bankrivver_439\nentry: seashore_3\nsummary: FAIL 423",
                "entry: br_12\nsummary: OK 4",
            ],
            "patterned_secrettext": [
                "HEADER 49583492\nOK 0\n",
                "HEADER FuturisticSpace\nFAIL 00030\n",
                "HEADER Secondary\nFAIL 1\n",
            ],
            "patterned_string_exclude_dot": ["host-1", "qwe@Awe?"],
        },
        "fail": {
            "patterned_string": ["XX", "Aa", "nc"],
            "patterned_password": ["a999!", "Cdkr493A", "cvhf@123!43"],
            "patterned_text": [
                "FAIL 14",
                # trailing `\n` will break the pattern
                "entry: br_12\nOK 4\n",
                "entry: eh_23\nsummary: OK",
                "entry: eh_23\nentry: he_2\nentry: smth_3\nentry: smth_4\nsummary: FAIL 4",
            ],
            "patterned_secrettext": ["FAIL 001\n", "HEADER TestResults\nOK 010\n", "HEADER TRestl2343\nFAIL 000\n"],
            "patterned_string_exclude_dot": ["host.1", "qwe."],
        },
    }

    def setUp(self) -> None:
        super().setUp()

        self.api_v2_bundles_dir = Path(__file__).parent / "bundles"

        bundle = self.add_bundle(self.api_v2_bundles_dir / "cluster_with_patterns")
        self.cluster = self.add_cluster(bundle=bundle, name="With Patterns")
        self.service = self.add_services_to_cluster(["with_patterns"], cluster=self.cluster).get()
        self.component = ServiceComponent.objects.get(service=self.service, prototype__name="cwp")

    def get_object_path(self, target: Cluster | ClusterObject | ServiceComponent) -> str:
        prefix = "/api/v2/clusters"
        if isinstance(target, Cluster):
            return f"{prefix}/{target.id}/"

        if isinstance(target, ClusterObject):
            return f"{prefix}/{target.cluster_id}/services/{target.id}/"

        if isinstance(target, ServiceComponent):
            return f"{prefix}/{target.cluster_id}/services/{target.service_id}/components/{target.id}/"

    def change_one_field(
        self, target: Cluster | ClusterObject | ServiceComponent, field_name: str, new_value: str
    ) -> Response:
        path = f"{self.get_object_path(target)}configs/"
        target.refresh_from_db(fields=["config"])
        current_data = self.client.get(f"{path}{target.config.current}/").json()["config"]

        return self.client.post(path=path, data={"config": current_data | {field_name: new_value}, "adcmMeta": {}})

    def change_one_field_in_group(self, group: GroupConfig, field_name: str, new_value: str) -> Response:
        path = f"{self.get_object_path(group.object)}config-groups/{group.id}/configs/"
        group.refresh_from_db(fields=["config"])
        current_data = self.client.get(f"{path}{group.config.current}/").json()

        return self.client.post(
            path=path,
            data={
                "config": current_data["config"] | {field_name: new_value},
                "adcmMeta": current_data["adcmMeta"] | {f"/{field_name}": {"isSynchronized": False}},
            },
        )

    def run_action(self, target: Cluster | ClusterObject | ServiceComponent, action: Action, config: dict) -> Response:
        path = f"{self.get_object_path(target)}actions/{action.id}/run/"
        return self.client.post(path=path, data={"configuration": {"config": config, "adcmMeta": {}}})

    def test_pattern_in_schema(self) -> None:
        for owner in (self.cluster, self.service, self.component):
            response = self.client.get(path=f"{self.get_object_path(owner)}config-schema/")
            self.assertEqual(response.status_code, HTTP_200_OK)

            fields_schema = response.json()["properties"]
            for key, schema in fields_schema.items():
                expected_pattern = self._PATTERNS.get(key)
                if expected_pattern:
                    self.assertIn("pattern", schema)
                    self.assertEqual(schema["pattern"], expected_pattern)
                else:
                    self.assertNotIn("pattern", schema)

    def test_pattern_in_action_schema(self) -> None:
        target = self.cluster
        action = Action.objects.get(prototype=self.cluster.prototype, name="with_jc")
        path = f"{self.get_object_path(target)}actions/{action.id}/"
        response = self.client.get(path=path)

        self.assertEqual(response.status_code, HTTP_200_OK)
        fields_schema = response.json()["configuration"]["configSchema"]["properties"]
        for key, schema in fields_schema.items():
            expected_pattern = self._PATTERNS.get(key)
            if expected_pattern:
                self.assertIn("pattern", schema)
                self.assertEqual(schema["pattern"], expected_pattern)
            else:
                self.assertNotIn("pattern", schema)

    def test_change_config_of_main_object(self) -> None:
        owners = (self.cluster, self.service, self.component)
        for field, cases in self._EXAMPLES["ok"].items():
            for i, correct_value in enumerate(cases):
                owner = owners[i % 3]
                with self.subTest(f"{owner.__class__.__name__}-{field}-pattern_{i}-success"):
                    response = self.change_one_field(target=owner, field_name=field, new_value=correct_value)

                    self.assertEqual(response.status_code, HTTP_201_CREATED)
                    self.assertEqual(ansible_decrypt(response.json()["config"][field]), correct_value)

        for field, cases in self._EXAMPLES["fail"].items():
            expected_pattern = self._PATTERNS[field]
            for i, incorrect_value in enumerate(cases):
                owner = owners[i % 3]
                with self.subTest(f"{owner.__class__.__name__}-{field}-pattern_{i}-fail"):
                    response = self.change_one_field(target=owner, field_name=field, new_value=incorrect_value)

                    self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                    self.assertEqual(
                        response.json()["desc"],
                        f"The value of {field}/ config parameter does not match pattern: {expected_pattern}",
                    )

    def test_change_config_of_group_config(self) -> None:
        groups = (
            GroupConfig.objects.create(
                object_type=ContentType.objects.get_for_model(model=self.cluster),
                object_id=self.cluster.pk,
                name="cluster group",
            ),
            GroupConfig.objects.create(
                object_type=ContentType.objects.get_for_model(model=self.service),
                object_id=self.service.pk,
                name="service group",
            ),
            GroupConfig.objects.create(
                object_type=ContentType.objects.get_for_model(model=self.component),
                object_id=self.component.pk,
                name="component group",
            ),
        )
        for field, cases in self._EXAMPLES["ok"].items():
            for i, correct_value in enumerate(cases):
                group = groups[i % 3]

                with self.subTest(f"{group.object.__class__.__name__}-{field}-pattern_{i}-success"):
                    response = self.change_one_field_in_group(group=group, field_name=field, new_value=correct_value)

                    self.assertEqual(response.status_code, HTTP_201_CREATED)
                    self.assertEqual(ansible_decrypt(response.json()["config"][field]), correct_value)

        for field, cases in self._EXAMPLES["fail"].items():
            expected_pattern = self._PATTERNS[field]
            for i, incorrect_value in enumerate(cases):
                group = groups[i % 3]
                with self.subTest(f"{group.object.__class__.__name__}-{field}-pattern_{i}-fail"):
                    response = self.change_one_field_in_group(group=group, field_name=field, new_value=incorrect_value)

                    self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                    self.assertEqual(
                        response.json()["desc"],
                        f"The value of {field}/ config parameter does not match pattern: {expected_pattern}",
                    )

    def test_jinja_config(self) -> None:
        ok_data = {key: values[-1] for key, values in self._EXAMPLES["ok"].items()} | {"control": "4"}
        action = Action.objects.get(prototype=self.cluster.prototype, name="with_jc")

        ConcernItem.objects.all().delete()

        for key in self._EXAMPLES["ok"]:
            with self.subTest(f"{key}-fail"):
                with RunTaskMock():
                    response = self.run_action(
                        target=self.cluster, action=action, config=ok_data | {key: self._EXAMPLES["fail"][key][-1]}
                    )

                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertEqual(
                    response.json()["desc"],
                    f"The value of {key}/ config parameter does not match pattern: {self._PATTERNS[key]}",
                )

        with self.subTest("success"):
            with RunTaskMock():
                response = self.run_action(target=self.cluster, action=action, config=ok_data)

            self.assertEqual(response.status_code, HTTP_200_OK)
