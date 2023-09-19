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

from api_v2.config.utils import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta
from api_v2.tests.base import BaseAPITestCase
from cm.inventory import get_obj_config
from cm.models import ADCM, ConfigLog, GroupConfig, Host, HostProvider, ServiceComponent
from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response
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
            sorted(list(response.json()["results"][0].keys())),
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
            "config": self.cluster_1_config.config,
            "creationTime": self.cluster_1_config.date.isoformat().replace("+00:00", "Z"),
            "description": self.cluster_1_config.description,
            "id": self.cluster_1_config.pk,
            "isCurrent": True,
        }
        self.assertDictEqual(response.json(), data)

    def test_create_success(self):
        data = {
            "config": {
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
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
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
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
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
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

    def test_schema_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-config-schema",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_config.pk},
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = [
            {
                "name": "string",
                "displayName": "string",
                "type": "string",
                "default": "string",
                "isReadOnly": False,
                "isActive": False,
                "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                "options": [],
                "children": [],
            },
            {
                "children": [],
                "default": None,
                "displayName": "map_not_required",
                "isActive": False,
                "isReadOnly": False,
                "name": "map_not_required",
                "options": [],
                "type": "map",
                "validation": {"isRequired": False, "maxValue": None, "minValue": None},
            },
            {
                "name": "list",
                "displayName": "list",
                "type": "list",
                "default": ["value1", "value2", "value3"],
                "isReadOnly": False,
                "isActive": False,
                "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                "options": [],
                "children": [],
            },
            {
                "name": "boolean",
                "displayName": "boolean",
                "type": "boolean",
                "default": True,
                "isReadOnly": False,
                "isActive": False,
                "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                "options": [],
                "children": [],
            },
            {
                "name": "group",
                "displayName": "group",
                "type": "group",
                "default": None,
                "isReadOnly": False,
                "isActive": False,
                "validation": {"isRequired": True, "minValue": None, "maxValue": None},
                "options": [],
                "children": [
                    {
                        "name": "float",
                        "displayName": "float",
                        "type": "float",
                        "default": 0.1,
                        "isReadOnly": False,
                        "isActive": False,
                        "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                        "options": [],
                        "children": [],
                    },
                    {
                        "name": "map",
                        "displayName": "map",
                        "type": "map",
                        "default": {"integerKey": "10", "stringKey": "string"},
                        "isReadOnly": False,
                        "isActive": False,
                        "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                        "options": [],
                        "children": [],
                    },
                    {
                        "name": "text",
                        "displayName": "text",
                        "type": "text",
                        "default": "text",
                        "isReadOnly": False,
                        "isActive": False,
                        "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                        "options": [],
                        "children": [],
                    },
                ],
            },
            {
                "name": "activatable_group",
                "displayName": "activatable_group",
                "type": "group",
                "default": None,
                "isReadOnly": False,
                "isActive": True,
                "validation": {"isRequired": True, "minValue": None, "maxValue": None},
                "options": [],
                "children": [
                    {
                        "name": "integer",
                        "displayName": "integer",
                        "type": "integer",
                        "default": 10,
                        "isReadOnly": False,
                        "isActive": False,
                        "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                        "options": [],
                        "children": [],
                    },
                    {
                        "name": "json",
                        "displayName": "json",
                        "type": "json",
                        "default": {"key": "value"},
                        "isReadOnly": False,
                        "isActive": False,
                        "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                        "options": [],
                        "children": [],
                    },
                    {
                        "name": "structure",
                        "displayName": "structure",
                        "type": "structure",
                        "default": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                        "isReadOnly": False,
                        "isActive": False,
                        "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                        "options": [],
                        "children": [],
                    },
                ],
            },
        ]
        self.assertListEqual(response.json(), data)


class TestMapTypeConfig(BaseAPITestCase):
    def test_absent_not_required_map_config_processing_success(self):
        new_config = {"string": "new string value"}
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"config": new_config, "attr": {}, "adcmMeta": {"/activatable_group": {"isActive": False}}},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.cluster_1.refresh_from_db()
        processed_config = get_obj_config(obj=self.cluster_1)
        self.assertDictEqual(processed_config, {"activatable_group": None, **new_config})

    def test_not_required_no_default_map_config_processing_success(self):
        processed_config = get_obj_config(obj=self.cluster_1)
        self.assertDictEqual(processed_config["map_not_required"], {})


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
                viewname="v2:cluster-config-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "config_group_pk": self.cluster_1_group_config.pk},
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertListEqual(
            sorted(list(response.json()["results"][0].keys())),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-config-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "config_group_pk": self.cluster_1_group_config.pk,
                    "pk": self.cluster_1_group_config_config.pk,
                },
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = {
            "id": self.cluster_1_group_config_config.pk,
            "isCurrent": True,
            "creationTime": self.cluster_1_group_config_config.date.isoformat().replace("+00:00", "Z"),
            "config": self.cluster_1_group_config_config.config,
            "adcmMeta": {
                "/string": {"isSynchronized": False},
                "/map_not_required": {"isSynchronized": False},
                "/list": {"isSynchronized": False},
                "/boolean": {"isSynchronized": False},
                "/group/float": {"isSynchronized": False},
                "/group/map": {"isSynchronized": False},
                "/group/text": {"isSynchronized": False},
                "/activatable_group": {"isSynchronized": False, "isActive": True},
                "/activatable_group/integer": {"isSynchronized": False},
                "/activatable_group/json": {"isSynchronized": False},
                "/activatable_group/structure": {"isSynchronized": False},
            },
            "description": self.cluster_1_group_config_config.description,
        }
        self.assertDictEqual(response.json(), data)

    def test_create_success(self):
        data = {
            "config": {
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
            },
            "adcmMeta": {
                "/string": {"isSynchronized": False},
                "/map_not_required": {"isSynchronized": False},
                "/list": {"isSynchronized": False},
                "/boolean": {"isSynchronized": False},
                "/group/float": {"isSynchronized": False},
                "/group/map": {"isSynchronized": False},
                "/group/text": {"isSynchronized": False},
                "/activatable_group": {"isSynchronized": False, "isActive": True},
                "/activatable_group/integer": {"isSynchronized": False},
                "/activatable_group/json": {"isSynchronized": False},
                "/activatable_group/structure": {"isSynchronized": False},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-config-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "config_group_pk": self.cluster_1_group_config.pk},
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
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
            },
            "adcmMeta": {
                "bad_key": "bad_value",
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-config-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "config_group_pk": self.cluster_1_group_config.pk},
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
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
            },
            "adcmMeta": {
                "/string": {"isSynchronized": False},
                "/list": {"isSynchronized": False},
                "/boolean": {"isSynchronized": False},
                "/group/float": {"isSynchronized": False},
                "/group/map": {"isSynchronized": False},
                "/group/text": {"isSynchronized": False},
                "/activatable_group": {"isSynchronized": False, "isActive": True},
                "/activatable_group/integer": {"isSynchronized": False},
                "/activatable_group/json": {"isSynchronized": False},
                "/activatable_group/structure": {"isSynchronized": False},
                "/stringBAD": {"isSynchronized": False},
            },
            "description": "new config",
        }

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-config-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "config_group_pk": self.cluster_1_group_config.pk},
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"code": "ATTRIBUTE_ERROR", "desc": "invalid `stringBAD/` field in `group_keys`", "level": "error"},
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
            sorted(list(response.json()["results"][0].keys())),
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

        data = {
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "config": self.service_1_initial_config.config,
            "creationTime": self.service_1_initial_config.date.isoformat().replace("+00:00", "Z"),
            "description": self.service_1_initial_config.description,
            "id": self.service_1_initial_config.pk,
            "isCurrent": True,
        }
        self.assertDictEqual(response.json(), data)

    def test_create_success(self):
        data = {
            "config": {
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
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
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)


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
            sorted(list(response.json()["results"][0].keys())),
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

        data = {
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "config": self.component_1_initial_config.config,
            "creationTime": self.component_1_initial_config.date.isoformat().replace("+00:00", "Z"),
            "description": self.component_1_initial_config.description,
            "id": self.component_1_initial_config.pk,
            "isCurrent": True,
        }
        self.assertDictEqual(response.json(), data)

    def test_create_success(self):
        data = {
            "config": {
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
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
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)

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
        self.assertEqual(response.json()["count"], 2)


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
            sorted(list(response.json()["results"][0].keys())),
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

        data = {
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "config": self.provider_initial_config.config,
            "creationTime": self.provider_initial_config.date.isoformat().replace("+00:00", "Z"),
            "description": self.provider_initial_config.description,
            "id": self.provider_initial_config.pk,
            "isCurrent": True,
        }
        self.assertDictEqual(response.json(), data)

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
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
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
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["adcmMeta"], data["adcmMeta"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["isCurrent"], True)


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
            sorted(list(response.json()["results"][0].keys())),
            sorted(["id", "isCurrent", "creationTime", "description"]),
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:host-config-detail", kwargs={"host_pk": self.host.pk, "pk": self.host_config.pk})
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        data = {
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "config": self.host_config.config,
            "creationTime": self.host_config.date.isoformat().replace("+00:00", "Z"),
            "description": self.host_config.description,
            "id": self.host_config.pk,
            "isCurrent": True,
        }
        self.assertDictEqual(response.json(), data)

    def test_create_success(self):
        data = {
            "config": {
                "group": {"float": 0.1, "map": {"integer_key": "10", "string_key": "string"}, "text": "text"},
                "activatable_group": {
                    "integer": 10,
                    "json": {"key": "value"},
                    "structure": [{"integer": 1, "string": "string1"}, {"integer": 2, "string": "string2"}],
                },
                "string": "string",
                "list": ["value1", "value2", "value3"],
                "boolean": True,
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


class TestADCMConfig(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")
        self.adcm = ADCM.objects.first()
        self.adcm_current_config = ConfigLog.objects.get(id=self.adcm.config.current)

    def test_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:adcm:adcm-config-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertListEqual(
            sorted(list(data["results"][0].keys())), sorted(["id", "isCurrent", "creationTime", "description"])
        )
        self.assertTrue(data["results"][0]["isCurrent"])

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:adcm:adcm-config-detail", kwargs={"pk": self.adcm_current_config.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["isCurrent"])
        self.assertDictEqual(
            data["adcmMeta"], {"/logrotate": {"isActive": False}, "/ldap_integration": {"isActive": False}}
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
                "auth_policy": {
                    "min_password_length": 12,
                    "max_password_length": 20,
                    "login_attempt_limit": 5,
                    "block_time": 5,
                },
            },
            "adcmMeta": {"/logrotate": {"isActive": False}, "/ldap_integration": {"isActive": False}},
            "description": "new ADCM config",
        }

        response = self.client.post(path=reverse(viewname="v2:adcm:adcm-config-list"), data=data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(ConfigLog.objects.filter(obj_ref=self.adcm.config).count(), 2)
        self.assertTrue(response.json()["isCurrent"])
        self.assertEqual(response.json()["description"], "new ADCM config")


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
