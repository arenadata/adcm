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

from api_v2.config.utils import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta
from api_v2.tests.base import BaseAPITestCase
from cm.adcm_config.ansible import ansible_decrypt
from cm.inventory import get_obj_config
from cm.models import ADCM, ConfigLog, GroupConfig, Host, HostProvider, ServiceComponent
from django.contrib.contenttypes.models import ContentType
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)


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
                "additionalProperties": False,
                "properties": {
                    "boolean": {
                        "title": "boolean",
                        "type": "boolean",
                        "description": "",
                        "default": True,
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
                    },
                    "group": {
                        "title": "group",
                        "type": "object",
                        "additionalProperties": False,
                        "description": "",
                        "default": {},
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
                        "properties": {
                            "float": {
                                "oneOf": [
                                    {
                                        "title": "float",
                                        "type": "number",
                                        "description": "",
                                        "default": 0.1,
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
                                    },
                                    {"type": "null"},
                                ]
                            }
                        },
                        "required": ["float"],
                    },
                    "variant_not_strict": {
                        "title": "variant_not_strict",
                        "type": "string",
                        "description": "",
                        "default": "value1",
                        "readOnly": False,
                        "adcmMeta": {
                            "isAdvanced": False,
                            "isInvisible": False,
                            "activation": None,
                            "synchronization": None,
                            "nullValue": None,
                            "isSecret": False,
                            "stringExtra": {"isMultiline": False, "suggestions": ["value1", "value2", "value3"]},
                            "enumExtra": None,
                        },
                    },
                    "list": {
                        "oneOf": [
                            {
                                "title": "list",
                                "type": "array",
                                "description": "",
                                "default": ["value1", "value2", "value3"],
                                "readOnly": False,
                                "adcmMeta": {
                                    "isAdvanced": False,
                                    "isInvisible": False,
                                    "activation": None,
                                    "synchronization": None,
                                    "nullValue": [],
                                    "isSecret": False,
                                    "stringExtra": None,
                                    "enumExtra": None,
                                },
                                "items": {
                                    "type": "string",
                                    "title": "",
                                    "description": "",
                                    "default": None,
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
                                },
                            },
                            {"type": "null"},
                        ]
                    },
                    "activatable_group": {
                        "title": "activatable_group",
                        "type": "object",
                        "additionalProperties": False,
                        "description": "",
                        "default": {},
                        "readOnly": False,
                        "adcmMeta": {
                            "isAdvanced": False,
                            "isInvisible": False,
                            "activation": {"isAllowChange": True},
                            "synchronization": None,
                            "nullValue": None,
                            "isSecret": False,
                            "stringExtra": None,
                            "enumExtra": None,
                        },
                        "properties": {
                            "integer": {
                                "oneOf": [
                                    {
                                        "title": "integer",
                                        "type": "integer",
                                        "description": "",
                                        "default": 10,
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
                                    },
                                    {"type": "null"},
                                ]
                            }
                        },
                        "required": ["integer"],
                    },
                },
                "required": ["boolean", "group", "variant_not_strict", "list", "activatable_group"],
            },
        )


class TestSaveConfigWithoutRequiredField(BaseAPITestCase):
    """ADCM-4328"""

    def setUp(self) -> None:
        super().setUp()

        self.service = self.add_service_to_cluster(
            service_name="service_4_save_config_without_required_field", cluster=self.cluster_1
        )

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
        processed_config = get_obj_config(obj=self.service)
        self.assertDictEqual(processed_config, {})

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

    def test_default_success(self):
        processed_config = get_obj_config(obj=self.service)
        self.assertDictEqual(processed_config["map_not_required"], {})
        self.assertDictEqual(
            processed_config,
            {
                "group": {"map_not_required": {}, "variant_not_required": None},
                "map_not_required": {},
                "variant_not_required": None,
                "list": ["value1", "value2"],
            },
        )


class TestClusterGroupConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_1_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.cluster_1),
            object_id=self.cluster_1.pk,
        )
        self.cluster_1_group_config_config = ConfigLog.objects.get(pk=self.cluster_1_group_config.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
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
                    "group_config_pk": self.cluster_1_group_config.pk,
                    "pk": self.cluster_1_group_config_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = {
            "id": self.cluster_1_group_config_config.pk,
            "isCurrent": True,
            "creationTime": self.cluster_1_group_config_config.date.isoformat().replace("+00:00", "Z"),
            "config": {
                "activatable_group": {"integer": 10},
                "boolean": True,
                "group": {"float": 0.1},
                "list": ["value1", "value2", "value3"],
                "variant_not_strict": "value1",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/boolean": {"isSynchronized": False},
                "/group/float": {"isSynchronized": False},
                "/variant_not_strict": {"isSynchronized": False},
                "/list": {"isSynchronized": False},
                "/activatable_group/integer": {"isSynchronized": False},
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
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/boolean": {"isSynchronized": True},
                "/group/float": {"isSynchronized": True},
                "/variant_not_strict": {"isSynchronized": True},
                "/list": {"isSynchronized": True},
                "/activatable_group/integer": {"isSynchronized": True},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data=data,
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
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
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
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
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
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_group_config.pk},
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
                "additionalProperties": False,
                "properties": {
                    "boolean": {
                        "title": "boolean",
                        "type": "boolean",
                        "description": "",
                        "default": True,
                        "readOnly": False,
                        "adcmMeta": {
                            "isAdvanced": False,
                            "isInvisible": False,
                            "activation": None,
                            "synchronization": {"isAllowChange": True},
                            "nullValue": None,
                            "isSecret": False,
                            "stringExtra": None,
                            "enumExtra": None,
                        },
                    },
                    "group": {
                        "title": "group",
                        "type": "object",
                        "additionalProperties": False,
                        "description": "",
                        "default": {},
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
                        "properties": {
                            "float": {
                                "oneOf": [
                                    {
                                        "title": "float",
                                        "type": "number",
                                        "description": "",
                                        "default": 0.1,
                                        "readOnly": False,
                                        "adcmMeta": {
                                            "isAdvanced": False,
                                            "isInvisible": False,
                                            "activation": None,
                                            "synchronization": {"isAllowChange": True},
                                            "nullValue": None,
                                            "isSecret": False,
                                            "stringExtra": None,
                                            "enumExtra": None,
                                        },
                                    },
                                    {"type": "null"},
                                ]
                            }
                        },
                        "required": ["float"],
                    },
                    "variant_not_strict": {
                        "title": "variant_not_strict",
                        "type": "string",
                        "description": "",
                        "default": "value1",
                        "readOnly": False,
                        "adcmMeta": {
                            "isAdvanced": False,
                            "isInvisible": False,
                            "activation": None,
                            "synchronization": {"isAllowChange": True},
                            "nullValue": None,
                            "isSecret": False,
                            "stringExtra": {"isMultiline": False, "suggestions": ["value1", "value2", "value3"]},
                            "enumExtra": None,
                        },
                    },
                    "list": {
                        "oneOf": [
                            {
                                "title": "list",
                                "type": "array",
                                "description": "",
                                "default": ["value1", "value2", "value3"],
                                "readOnly": False,
                                "adcmMeta": {
                                    "isAdvanced": False,
                                    "isInvisible": False,
                                    "activation": None,
                                    "synchronization": {"isAllowChange": True},
                                    "nullValue": [],
                                    "isSecret": False,
                                    "stringExtra": None,
                                    "enumExtra": None,
                                },
                                "items": {
                                    "type": "string",
                                    "title": "",
                                    "description": "",
                                    "default": None,
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
                                },
                            },
                            {"type": "null"},
                        ]
                    },
                    "activatable_group": {
                        "title": "activatable_group",
                        "type": "object",
                        "additionalProperties": False,
                        "description": "",
                        "default": {},
                        "readOnly": False,
                        "adcmMeta": {
                            "isAdvanced": False,
                            "isInvisible": False,
                            "activation": {"isAllowChange": True},
                            "synchronization": {"isAllowChange": True},
                            "nullValue": None,
                            "isSecret": False,
                            "stringExtra": None,
                            "enumExtra": None,
                        },
                        "properties": {
                            "integer": {
                                "oneOf": [
                                    {
                                        "title": "integer",
                                        "type": "integer",
                                        "description": "",
                                        "default": 10,
                                        "readOnly": False,
                                        "adcmMeta": {
                                            "isAdvanced": False,
                                            "isInvisible": False,
                                            "activation": None,
                                            "synchronization": {"isAllowChange": True},
                                            "nullValue": None,
                                            "isSecret": False,
                                            "stringExtra": None,
                                            "enumExtra": None,
                                        },
                                    },
                                    {"type": "null"},
                                ]
                            }
                        },
                        "required": ["integer"],
                    },
                },
                "required": ["boolean", "group", "variant_not_strict", "list", "activatable_group"],
            },
        )


class TestServiceConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
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

        expected_data = {
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
            "additionalProperties": False,
            "properties": {
                "string": {
                    "oneOf": [
                        {
                            "title": "string",
                            "type": "string",
                            "description": "",
                            "default": "string",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                        },
                        {"type": "null"},
                    ]
                },
                "group": {
                    "title": "group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "password": {
                            "title": "password",
                            "type": "string",
                            "description": "",
                            "default": "password",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": True,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        }
                    },
                    "required": ["password"],
                },
                "activatable_group": {
                    "title": "activatable_group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": {"isAllowChange": True},
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "text": {
                            "oneOf": [
                                {
                                    "title": "text",
                                    "type": "string",
                                    "description": "",
                                    "default": "text",
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": True},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        }
                    },
                    "required": ["text"],
                },
            },
            "required": ["string", "group", "activatable_group"],
        }
        actual_data = response.json()
        actual_data["properties"]["group"]["properties"]["password"]["default"] = ansible_decrypt(
            msg=actual_data["properties"]["group"]["properties"]["password"]["default"]
        )
        self.assertDictEqual(actual_data, expected_data)


class TestServiceGroupConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)

        self.service_1_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.service_1),
            object_id=self.service_1.pk,
        )
        self.service_1_group_config_config = ConfigLog.objects.get(pk=self.service_1_group_config.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.service_1_group_config.pk,
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
                    "group_config_pk": self.service_1_group_config.pk,
                    "pk": self.service_1_group_config_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        expected_data = {
            "id": self.service_1_group_config_config.pk,
            "isCurrent": True,
            "creationTime": self.service_1_group_config_config.date.isoformat().replace("+00:00", "Z"),
            "config": {
                "group": {"password": "password"},
                "activatable_group": {"text": "text"},
                "string": "string",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/activatable_group/text": {"isSynchronized": False},
                "/group/password": {"isSynchronized": False},
                "/string": {"isSynchronized": False},
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
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/activatable_group/text": {"isSynchronized": True},
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
                    "group_config_pk": self.service_1_group_config.pk,
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
                    "group_config_pk": self.service_1_group_config.pk,
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
                    "group_config_pk": self.service_1_group_config.pk,
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
                    "pk": self.service_1_group_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = {
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
            "additionalProperties": False,
            "properties": {
                "string": {
                    "oneOf": [
                        {
                            "title": "string",
                            "type": "string",
                            "description": "",
                            "default": "string",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": {"isAllowChange": True},
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                        },
                        {"type": "null"},
                    ]
                },
                "group": {
                    "title": "group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "password": {
                            "title": "password",
                            "type": "string",
                            "description": "",
                            "default": "password",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": {"isAllowChange": True},
                                "nullValue": None,
                                "isSecret": True,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        }
                    },
                    "required": ["password"],
                },
                "activatable_group": {
                    "title": "activatable_group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": {"isAllowChange": True},
                        "synchronization": {"isAllowChange": True},
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "text": {
                            "oneOf": [
                                {
                                    "title": "text",
                                    "type": "string",
                                    "description": "",
                                    "default": "text",
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": {"isAllowChange": True},
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": True},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        }
                    },
                    "required": ["text"],
                },
            },
            "required": ["string", "group", "activatable_group"],
        }
        actual_data = response.json()
        actual_data["properties"]["group"]["properties"]["password"]["default"] = ansible_decrypt(
            msg=actual_data["properties"]["group"]["properties"]["password"]["default"]
        )
        self.assertDictEqual(actual_data, expected_data)


class TestComponentConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
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

        expected_data = {
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
            "additionalProperties": False,
            "properties": {
                "secrettext": {
                    "title": "secrettext",
                    "type": "string",
                    "description": "",
                    "default": "secrettext",
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": None,
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": True,
                        "stringExtra": {"isMultiline": True},
                        "enumExtra": None,
                    },
                    "minLength": 1,
                },
                "group": {
                    "title": "group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "file": {
                            "oneOf": [
                                {
                                    "title": "file",
                                    "type": "string",
                                    "description": "",
                                    "default": "content",
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": True},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        }
                    },
                    "required": ["file"],
                },
                "activatable_group": {
                    "title": "activatable_group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": {"isAllowChange": True},
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "secretfile": {
                            "title": "secretfile",
                            "type": "string",
                            "description": "",
                            "default": "content",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": True,
                                "stringExtra": {"isMultiline": True},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        }
                    },
                    "required": ["secretfile"],
                },
            },
            "required": ["secrettext", "group", "activatable_group"],
        }
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

        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
        self.component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )

        self.component_1_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.component_1),
            object_id=self.component_1.pk,
        )
        self.component_1_group_config_config = ConfigLog.objects.get(pk=self.component_1_group_config.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
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
                    "group_config_pk": self.component_1_group_config.pk,
                    "pk": self.component_1_group_config_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        expected_data = {
            "id": self.component_1_group_config_config.pk,
            "isCurrent": True,
            "creationTime": self.component_1_group_config_config.date.isoformat().replace("+00:00", "Z"),
            "config": {
                "group": {"file": "content"},
                "activatable_group": {"secretfile": "content"},
                "secrettext": "secrettext",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/activatable_group/secretfile": {"isSynchronized": False},
                "/group/file": {"isSynchronized": False},
                "/secrettext": {"isSynchronized": False},
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
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/activatable_group/secretfile": {"isSynchronized": True},
                "/group/file": {"isSynchronized": True},
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
                    "group_config_pk": self.component_1_group_config.pk,
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
                    "group_config_pk": self.component_1_group_config.pk,
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
                    "group_config_pk": self.component_1_group_config.pk,
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
                    "pk": self.component_1_group_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = {
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
            "additionalProperties": False,
            "properties": {
                "secrettext": {
                    "title": "secrettext",
                    "type": "string",
                    "description": "",
                    "default": "secrettext",
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": None,
                        "synchronization": {"isAllowChange": True},
                        "nullValue": None,
                        "isSecret": True,
                        "stringExtra": {"isMultiline": True},
                        "enumExtra": None,
                    },
                    "minLength": 1,
                },
                "group": {
                    "title": "group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "file": {
                            "oneOf": [
                                {
                                    "title": "file",
                                    "type": "string",
                                    "description": "",
                                    "default": "content",
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": {"isAllowChange": True},
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": True},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        }
                    },
                    "required": ["file"],
                },
                "activatable_group": {
                    "title": "activatable_group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": {"isAllowChange": True},
                        "synchronization": {"isAllowChange": True},
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "secretfile": {
                            "title": "secretfile",
                            "type": "string",
                            "description": "",
                            "default": "content",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": {"isAllowChange": True},
                                "nullValue": None,
                                "isSecret": True,
                                "stringExtra": {"isMultiline": True},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        }
                    },
                    "required": ["secretfile"],
                },
            },
            "required": ["secrettext", "group", "activatable_group"],
        }
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

        expected_data = {
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
            "additionalProperties": False,
            "properties": {
                "json": {
                    "oneOf": [
                        {
                            "title": "json",
                            "type": "string",
                            "description": "",
                            "default": '{"key": "value"}',
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": True},
                                "enumExtra": None,
                            },
                            "format": "json",
                        },
                        {"type": "null"},
                    ]
                },
                "group": {
                    "title": "group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "map": {
                            "title": "map",
                            "type": "object",
                            "description": "",
                            "default": {"integer_key": "10", "string_key": "string"},
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": {},
                                "isSecret": False,
                                "stringExtra": None,
                                "enumExtra": None,
                            },
                            "additionalProperties": True,
                            "properties": {},
                        }
                    },
                    "required": ["map"],
                },
                "activatable_group": {
                    "title": "activatable_group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": {"isAllowChange": True},
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "secretmap": {
                            "title": "secretmap",
                            "type": "object",
                            "description": "",
                            "default": {
                                "integer_key": "10",
                                "string_key": "string",
                            },
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": True,
                                "stringExtra": None,
                                "enumExtra": None,
                            },
                            "additionalProperties": True,
                            "properties": {},
                        }
                    },
                    "required": ["secretmap"],
                },
            },
            "required": ["json", "group", "activatable_group"],
        }
        actual_data = response.json()

        actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["default"][
            "integer_key"
        ] = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["default"]["integer_key"]
        )
        actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["default"][
            "string_key"
        ] = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["default"]["string_key"]
        )

        self.assertDictEqual(actual_data, expected_data)


class TestProviderGroupConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.provider_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.provider),
            object_id=self.provider.pk,
        )
        self.provider_group_config_config = ConfigLog.objects.get(pk=self.provider_group_config.config.current)

    def test_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={"hostprovider_pk": self.provider.pk, "group_config_pk": self.provider_group_config.pk},
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
                    "group_config_pk": self.provider_group_config.pk,
                    "pk": self.provider_group_config_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = {
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/json": {"isSynchronized": False},
                "/group/map": {"isSynchronized": False},
                "/activatable_group/secretmap": {"isSynchronized": False},
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
            "creationTime": self.provider_group_config_config.date.isoformat().replace("+00:00", "Z"),
            "description": "init",
            "id": self.provider_group_config_config.pk,
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
                    "group_config_pk": self.provider_group_config.pk,
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
                    "pk": self.provider_group_config.pk,
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
                "/activatable_group": {"isActive": True, "isSynchronized": True},
                "/json": {"isSynchronized": True},
                "/group/map": {"isSynchronized": True},
                "/activatable_group/secretmap": {"isSynchronized": True},
            },
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "group_config_pk": self.provider_group_config.pk,
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
                viewname="v2:hostprovider-group-config-config-schema",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_group_config.pk},
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = {
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
            "additionalProperties": False,
            "properties": {
                "json": {
                    "oneOf": [
                        {
                            "title": "json",
                            "type": "string",
                            "description": "",
                            "default": '{"key": "value"}',
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": {"isAllowChange": True},
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": True},
                                "enumExtra": None,
                            },
                            "format": "json",
                        },
                        {"type": "null"},
                    ]
                },
                "group": {
                    "title": "group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "map": {
                            "title": "map",
                            "type": "object",
                            "description": "",
                            "default": {"integer_key": "10", "string_key": "string"},
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": {"isAllowChange": True},
                                "nullValue": {},
                                "isSecret": False,
                                "stringExtra": None,
                                "enumExtra": None,
                            },
                            "additionalProperties": True,
                            "properties": {},
                        }
                    },
                    "required": ["map"],
                },
                "activatable_group": {
                    "title": "activatable_group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": {"isAllowChange": True},
                        "synchronization": {"isAllowChange": True},
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "secretmap": {
                            "title": "secretmap",
                            "type": "object",
                            "description": "",
                            "default": {
                                "integer_key": "10",
                                "string_key": "string",
                            },
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": {"isAllowChange": True},
                                "nullValue": None,
                                "isSecret": True,
                                "stringExtra": None,
                                "enumExtra": None,
                            },
                            "additionalProperties": True,
                            "properties": {},
                        }
                    },
                    "required": ["secretmap"],
                },
            },
            "required": ["json", "group", "activatable_group"],
        }
        actual_data = response.json()

        actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["default"][
            "integer_key"
        ] = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["default"]["integer_key"]
        )
        actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["default"][
            "string_key"
        ] = ansible_decrypt(
            msg=actual_data["properties"]["activatable_group"]["properties"]["secretmap"]["default"]["string_key"]
        )

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

        expected_data = {
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
            "additionalProperties": False,
            "properties": {
                "structure": {
                    "title": "structure",
                    "type": "array",
                    "description": "",
                    "default": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
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
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "title": "",
                        "description": "",
                        "default": {},
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
                        "properties": {
                            "string": {
                                "type": "string",
                                "title": "string",
                                "description": "",
                                "default": None,
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
                            },
                            "integer": {
                                "type": "integer",
                                "title": "integer",
                                "description": "",
                                "default": None,
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
                            },
                        },
                        "required": [],
                    },
                },
                "variant": {
                    "title": "variant",
                    "description": "",
                    "default": "value1",
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": None,
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": {"isMultiline": False},
                        "enumExtra": None,
                    },
                    "enum": ["value1", "value2", "value3"],
                    "minLength": 1,
                },
                "group": {
                    "title": "group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "list": {
                            "oneOf": [
                                {
                                    "title": "list",
                                    "type": "array",
                                    "description": "",
                                    "default": ["value1", "value2", "value3"],
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": [],
                                        "isSecret": False,
                                        "stringExtra": None,
                                        "enumExtra": None,
                                    },
                                    "items": {
                                        "type": "string",
                                        "title": "",
                                        "description": "",
                                        "default": None,
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
                                    },
                                },
                                {"type": "null"},
                            ]
                        }
                    },
                    "required": ["list"],
                },
                "activatable_group": {
                    "title": "activatable_group",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": {"isAllowChange": True},
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "option": {
                            "title": "option",
                            "description": "",
                            "default": "string1",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": None,
                                "enumExtra": {"labels": ["string1", "string2"]},
                            },
                            "enum": ["string1", "string2"],
                        }
                    },
                    "required": ["option"],
                },
            },
            "required": ["structure", "variant", "group", "activatable_group"],
        }
        actual_data = response.json()

        self.assertDictEqual(actual_data, expected_data)


class TestADCMConfig(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")
        self.adcm = ADCM.objects.first()
        self.adcm_current_config = ConfigLog.objects.get(id=self.adcm.config.current)

    def test_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:adcm:config-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertListEqual(
            sorted(data["results"][0].keys()), sorted(["id", "isCurrent", "creationTime", "description"])
        )
        self.assertTrue(data["results"][0]["isCurrent"])

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:adcm:config-detail", kwargs={"pk": self.adcm_current_config.pk})
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

        response = self.client.post(path=reverse(viewname="v2:adcm:config-list"), data=data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(ConfigLog.objects.filter(obj_ref=self.adcm.config).count(), 2)
        self.assertTrue(response.json()["isCurrent"])
        self.assertEqual(response.json()["description"], "new ADCM config")

    def test_schema(self):
        response = self.client.get(path=reverse(viewname="v2:adcm:config-schema"))
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_data = {
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
            "additionalProperties": False,
            "properties": {
                "global": {
                    "title": "Global Options",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "adcm_url": {
                            "title": "ADCM's URL",
                            "type": "string",
                            "description": (
                                "We have to know ADCM's Url to send information from host. We try to guess "
                                "that information from url you enter in browser.\nBut if your network has "
                                "more complicated structure and we guess wrong, please fix that here.\n"
                            ),
                            "default": None,
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "verification_public_key": {
                            "title": "Bundle verification public key",
                            "type": "string",
                            "description": (
                                "Bundle verification GPG public key to verify the signature of "
                                "the bundle (*.sig file) when uploading the bundle to ADCM.\n"
                            ),
                            "default": "\n",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": True},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                    },
                    "required": ["adcm_url", "verification_public_key"],
                },
                "statistics_collection": {
                    "title": "Statistics Collection",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": True,
                        "isInvisible": False,
                        "activation": {"isAllowChange": True},
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "url": {
                            "title": "url",
                            "type": "string",
                            "description": "URL to send collected statistic",
                            "default": "adcm-usage-ss.arenadata.io",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": True,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        }
                    },
                    "required": ["url"],
                },
                "google_oauth": {
                    "title": "Google Auth",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": True,
                        "activation": None,
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "client_id": {
                            "oneOf": [
                                {
                                    "title": "client_id",
                                    "type": "string",
                                    "description": "",
                                    "default": None,
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": False},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        },
                        "secret": {
                            "oneOf": [
                                {
                                    "title": "secret",
                                    "type": "string",
                                    "description": "",
                                    "default": None,
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": True,
                                        "stringExtra": {"isMultiline": False},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        },
                    },
                    "required": ["client_id", "secret"],
                },
                "yandex_oauth": {
                    "title": "Yandex Auth",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": True,
                        "activation": None,
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "client_id": {
                            "oneOf": [
                                {
                                    "title": "client_id",
                                    "type": "string",
                                    "description": "",
                                    "default": None,
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": False},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        },
                        "secret": {
                            "oneOf": [
                                {
                                    "title": "secret",
                                    "type": "string",
                                    "description": "",
                                    "default": None,
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": True,
                                        "stringExtra": {"isMultiline": False},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        },
                    },
                    "required": ["client_id", "secret"],
                },
                "ansible_settings": {
                    "title": "Ansible Settings",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "forks": {
                            "title": "Forks",
                            "type": "integer",
                            "description": (
                                "This is the default number of parallel processes "
                                "to spawn when communicating with remote hosts.\n"
                            ),
                            "default": 5,
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
                            "minimum": 1,
                            "maximum": 100,
                        }
                    },
                    "required": ["forks"],
                },
                "logrotate": {
                    "title": "Nginx Server Logrotate",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": True,
                        "activation": {"isAllowChange": True},
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "size": {
                            "title": "Max file size",
                            "type": "string",
                            "description": "Specifies the allowed size the log file can reach before it is archived\n",
                            "default": "10M",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "max_history": {
                            "title": "Max files history",
                            "type": "integer",
                            "description": "Controls the maximum number of archive files to keep\n",
                            "default": 10,
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
                            "minimum": 1,
                        },
                        "compress": {
                            "title": "Enable compression",
                            "type": "boolean",
                            "description": "Compress the rotated files\n",
                            "default": False,
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
                        },
                    },
                    "required": ["size", "max_history", "compress"],
                },
                "audit_data_retention": {
                    "title": "Data retention policy",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "log_rotation_on_fs": {
                            "oneOf": [
                                {
                                    "title": "Job log retention period from file system",
                                    "type": "integer",
                                    "description": (
                                        "You can set the time (number of days) after which "
                                        "the logs will be deleted from the file system.\n"
                                    ),
                                    "default": 365,
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
                                    "minimum": 0,
                                },
                                {"type": "null"},
                            ]
                        },
                        "log_rotation_in_db": {
                            "oneOf": [
                                {
                                    "title": "Job log retention period from database",
                                    "type": "integer",
                                    "description": (
                                        "You can set the time (number of days) after which "
                                        "the logs will be deleted from the database.\n"
                                    ),
                                    "default": 365,
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
                                    "minimum": 0,
                                },
                                {"type": "null"},
                            ]
                        },
                        "config_rotation_in_db": {
                            "oneOf": [
                                {
                                    "title": "Objects configurations retention period",
                                    "type": "integer",
                                    "description": (
                                        "You can set the time (number of days) after which "
                                        "the Objects configuration will be deleted from the "
                                        "database. 0 is infinite storing.\n"
                                    ),
                                    "default": 0,
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
                                    "minimum": 0,
                                },
                                {"type": "null"},
                            ]
                        },
                        "retention_period": {
                            "title": "Audit data retention period",
                            "type": "integer",
                            "description": "Data storage period (in days) for operations and authorizations in ADCM.\n",
                            "default": 1825,
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
                        },
                        "data_archiving": {
                            "oneOf": [
                                {
                                    "title": "Enable audit data archiving",
                                    "type": "boolean",
                                    "description": (
                                        "Enable/disable archiving of data on operations and "
                                        'authorizations after the period specified in "Audit '
                                        'data retention period".\n'
                                    ),
                                    "default": False,
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
                                },
                                {"type": "null"},
                            ]
                        },
                    },
                    "required": [
                        "log_rotation_on_fs",
                        "log_rotation_in_db",
                        "config_rotation_in_db",
                        "retention_period",
                        "data_archiving",
                    ],
                },
                "ldap_integration": {
                    "title": "LDAP integration",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": {"isAllowChange": True},
                        "synchronization": None,
                        "nullValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "properties": {
                        "ldap_uri": {
                            "title": "LDAP URI",
                            "type": "string",
                            "description": "The URI of the LDAP server.\n",
                            "default": None,
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "ldap_user": {
                            "title": "Bind DN",
                            "type": "string",
                            "description": (
                                "The distinguished name (DN) of the user that is used to connect "
                                'to the LDAP server. For example: "cn=admin,dc=ad,dc=ranger-test".\n'
                            ),
                            "default": None,
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "ldap_password": {
                            "title": "Bind Password",
                            "type": "string",
                            "description": (
                                "Password for access to the LDAP server of the "
                                'user specified in the "LDAP User" field.\n'
                            ),
                            "default": None,
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": True,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "user_search_base": {
                            "title": "User search base",
                            "type": "string",
                            "description": (
                                "The distinguished name (DN) of the directory object from which to "
                                'search for entries. For example: "ou=Peoples,dc=ad,dc=ranger-test".\n'
                            ),
                            "default": None,
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "user_search_filter": {
                            "oneOf": [
                                {
                                    "title": "User search filter",
                                    "type": "string",
                                    "description": "Additional filter constraining the users selected for syncing.\n",
                                    "default": None,
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": False},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        },
                        "user_object_class": {
                            "title": "User object class",
                            "type": "string",
                            "description": "Object class to identify user entries.\n",
                            "default": "user",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "user_name_attribute": {
                            "title": "User name attribute",
                            "type": "string",
                            "description": "Attribute from user entry that would be treated as user name.\n",
                            "default": "sAMAccountName",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "group_search_base": {
                            "oneOf": [
                                {
                                    "title": "Group search base",
                                    "type": "string",
                                    "description": (
                                        "The distinguished name (DN) of the directory object from "
                                        'which to search for entries. For example: "ou=Groups,dc=ad,'
                                        'dc=ranger-test".\n'
                                    ),
                                    "default": None,
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": False},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        },
                        "group_search_filter": {
                            "oneOf": [
                                {
                                    "title": "Group search filter",
                                    "type": "string",
                                    "description": "Additional filter constraining the groups selected for syncing.\n",
                                    "default": None,
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": False},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        },
                        "group_object_class": {
                            "title": "Group object class",
                            "type": "string",
                            "description": "Object class to identify group entries.\n",
                            "default": "group",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "group_name_attribute": {
                            "title": "Group name attribute",
                            "type": "string",
                            "description": "Attribute from group entry that would be treated as group name.\n",
                            "default": "cn",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "group_member_attribute_name": {
                            "title": "Group member attribute name",
                            "type": "string",
                            "description": "Attribute from group entry that is list of members.\n",
                            "default": "member",
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "nullValue": None,
                                "isSecret": False,
                                "stringExtra": {"isMultiline": False},
                                "enumExtra": None,
                            },
                            "minLength": 1,
                        },
                        "sync_interval": {
                            "title": "Sync interval",
                            "type": "integer",
                            "description": (
                                "Amount of time in minutes that group memberships and user "
                                "distinguished names are synchronized between AD and ADCM.\n"
                            ),
                            "default": 60,
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
                        },
                        "tls_ca_cert_file": {
                            "oneOf": [
                                {
                                    "title": "TLS CA certificate file path",
                                    "type": "string",
                                    "description": "CA certificate path in ADCM container volume.\n",
                                    "default": None,
                                    "readOnly": False,
                                    "adcmMeta": {
                                        "isAdvanced": False,
                                        "isInvisible": False,
                                        "activation": None,
                                        "synchronization": None,
                                        "nullValue": None,
                                        "isSecret": False,
                                        "stringExtra": {"isMultiline": False},
                                        "enumExtra": None,
                                    },
                                },
                                {"type": "null"},
                            ]
                        },
                    },
                    "required": [
                        "ldap_uri",
                        "ldap_user",
                        "ldap_password",
                        "user_search_base",
                        "user_search_filter",
                        "user_object_class",
                        "user_name_attribute",
                        "group_search_base",
                        "group_search_filter",
                        "group_object_class",
                        "group_name_attribute",
                        "group_member_attribute_name",
                        "sync_interval",
                        "tls_ca_cert_file",
                    ],
                },
                "auth_policy": {
                    "title": "Authentication policy",
                    "type": "object",
                    "additionalProperties": False,
                    "description": "",
                    "default": {},
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
                    "properties": {
                        "min_password_length": {
                            "title": "Minimum password length",
                            "type": "integer",
                            "description": "",
                            "default": 12,
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
                            "minimum": 1,
                            "maximum": 128,
                        },
                        "max_password_length": {
                            "title": "Maximum password length",
                            "type": "integer",
                            "description": "",
                            "default": 128,
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
                            "minimum": 1,
                            "maximum": 128,
                        },
                        "login_attempt_limit": {
                            "title": "Login attempt limit",
                            "type": "integer",
                            "description": "The number of login attempts allowed before user account is locked out",
                            "default": 5,
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
                            "minimum": 1,
                        },
                        "block_time": {
                            "title": "Blocking time period",
                            "type": "integer",
                            "description": (
                                "Defines a period (in min) of inactivity after which "
                                "old failed login attempts will be cleared"
                            ),
                            "default": 5,
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
                            "minimum": 1,
                        },
                    },
                    "required": ["min_password_length", "max_password_length", "login_attempt_limit", "block_time"],
                },
            },
            "required": [
                "global",
                "statistics_collection",
                "google_oauth",
                "yandex_oauth",
                "ansible_settings",
                "logrotate",
                "audit_data_retention",
                "ldap_integration",
                "auth_policy",
            ],
        }
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
            "/activatable_group": {"isActive": True, "isSynchronized": True},
            "/activatable_group/string": {"isSynchronized": True},
            "/group/string": {"isSynchronized": False},
            "/string": {"isSynchronized": True},
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

        self.service = self.add_service_to_cluster(
            service_name="service_5_variant_type_without_values", cluster=self.cluster_1
        )

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
                            "nullValue": None,
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
