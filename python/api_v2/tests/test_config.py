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

from api_v2.tests.base import BaseAPITestCase
from cm.models import ConfigLog, GroupConfig
from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED


class TestClusterConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_1_config = ConfigLog.objects.get(id=self.cluster_1.config.current)

    def test_list_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk})
        )

        data = {
            "creation_time": self.cluster_1_config.date.isoformat().replace("+00:00", "Z"),
            "description": self.cluster_1_config.description,
            "id": self.cluster_1_config.pk,
            "is_current": True,
        }
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertDictEqual(response.json()["results"][0], data)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:cluster-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_config.pk},
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = {
            "attr": self.cluster_1_config.attr,
            "config": self.cluster_1_config.config,
            "creation_time": self.cluster_1_config.date.isoformat().replace("+00:00", "Z"),
            "description": self.cluster_1_config.description,
            "id": self.cluster_1_config.pk,
            "is_current": True,
        }
        self.assertDictEqual(response.json(), data)

    def test_create_success(self):
        data = {
            "config": {"string": "new string", "group": {"string": "new string"}},
            "attr": {},
            "description": "new config",
        }
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}), data=data
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["attr"], data["attr"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["is_current"], True)

    def test_schema_success(self):
        response: Response = self.client.get(
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
                "child": [],
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
                "child": ["string"],
            },
            {
                "name": "string",
                "displayName": "string",
                "type": "string",
                "default": "string",
                "isReadOnly": False,
                "isActive": False,
                "validation": {"isRequired": False, "minValue": None, "maxValue": None},
                "options": [],
                "child": [],
            },
        ]
        self.assertListEqual(response.json(), data)


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
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:cluster-config-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "config_group_pk": self.cluster_1_group_config.pk},
            )
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_retrieve_success(self):
        response: Response = self.client.get(
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
        attr = {
            "custom_group_keys": {"group": {"fields": {"string": True}, "value": True}, "string": True},
            "group_keys": {"group": {"fields": {"string": False}, "value": None}, "string": False},
        }
        self.assertDictEqual(response.json()["attr"], attr)

    def test_create_success(self):
        data = {
            "config": {"string": "new string", "group": {"string": "new string"}},
            "attr": {
                "custom_group_keys": {"group": {"fields": {"string": True}, "value": True}, "string": True},
                "group_keys": {"group": {"fields": {"string": True}, "value": None}, "string": True},
            },
            "description": "new config",
        }

        response: Response = self.client.post(
            path=reverse(
                viewname="v2:cluster-config-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "config_group_pk": self.cluster_1_group_config.pk},
            ),
            data=data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response_data = response.json()
        self.assertDictEqual(response_data["config"], data["config"])
        self.assertDictEqual(response_data["attr"], data["attr"])
        self.assertEqual(response_data["description"], data["description"])
        self.assertEqual(response_data["is_current"], True)
