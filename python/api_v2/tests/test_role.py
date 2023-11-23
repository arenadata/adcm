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
from django.urls import reverse
from rbac.models import Role
from rbac.services.role import role_create
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


class TestRole(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.view_cluster_config_role = Role.objects.get(name="View cluster configurations", built_in=True)
        self.edit_cluster_config_role = Role.objects.get(name="Edit cluster configurations", built_in=True)

        self.cluster_config_role = role_create(
            name="Change cluster config",
            display_name="Change cluster config",
            child=[self.view_cluster_config_role],
        )

    def test_retrieve_not_found_fail(self):
        response = self.client.get(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.cluster_config_role.pk + 10})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.cluster_config_role.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.cluster_config_role.pk)

    def test_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:rbac:role-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertGreater(len(response.json()["results"]), 1)

    def test_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:role-list"),
            data={"display_name": "Edit cluster configuration", "children": [self.edit_cluster_config_role.pk]},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertTrue(Role.objects.filter(id=response.json()["id"]).exists())

    def test_create_required_field_failed(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:role-list"), data={"display_name": "test"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "children - This field is required.;", "level": "error"}
        )

    def test_create_already_exists_failed(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:role-list"),
            data={
                "display_name": "Change cluster config",
                "children": [self.view_cluster_config_role.pk],
            },
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "ROLE_CREATE_ERROR",
                "desc": "A role with this name already exists",
                "level": "error",
            },
        )

    def test_update_required_filed_success(self):
        response = self.client.put(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.cluster_config_role.pk}),
            data={
                "display_name": "New change cluster config",
                "children": [self.edit_cluster_config_role.pk],
            },
        )

        self.cluster_config_role.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual("New change cluster config", self.cluster_config_role.display_name)
        self.assertEqual([self.edit_cluster_config_role], list(self.cluster_config_role.child.all()))

    def test_update_required_filed_failed(self):
        response = self.client.put(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.cluster_config_role.pk}),
            data={"display_name": "New change cluster config"},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "children - This field is required.;", "level": "error"}
        )

    def test_partial_update_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.cluster_config_role.pk}),
            data={"display_name": "New change cluster config"},
        )

        self.cluster_config_role.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual("New change cluster config", self.cluster_config_role.display_name)

    def test_update_built_in_failed(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.view_cluster_config_role.pk}),
            data={"built_in": False},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "ROLE_UPDATE_ERROR",
                "desc": "Can't modify role View cluster configurations as it is auto created",
                "level": "error",
            },
        )

    def test_delete_success(self):
        response = self.client.delete(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.cluster_config_role.pk})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Role.objects.filter(pk=self.cluster_config_role.pk).exists())

    def test_delete_failed(self):
        built_in_role = Role.objects.filter(built_in=True).first()

        response = self.client.delete(path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": built_in_role.pk}))

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "ROLE_DELETE_ERROR", "desc": "It is forbidden to remove the built-in role.", "level": "error"},
        )

    def test_ordering_success(self):
        limit = 10

        response = self.client.get(
            path=reverse(
                viewname="v2:rbac:role-list",
            ),
            data={"ordering": "-displayName", "limit": limit},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response_names = [role_data["displayName"] for role_data in response.json()["results"]]
        db_names = [role.display_name for role in Role.objects.order_by("-display_name")[:limit]]
        self.assertListEqual(response_names, db_names)

    def test_filtering_by_display_name_success(self):
        filter_name = "cReAtE"

        response = self.client.get(path=reverse(viewname="v2:rbac:role-list"), data={"displayName": filter_name})

        self.assertEqual(response.status_code, HTTP_200_OK)

        response_pks = [role_data["id"] for role_data in response.json()["results"]]
        db_pks = [role.pk for role in Role.objects.filter(display_name__icontains=filter_name)]
        self.assertListEqual(response_pks, db_pks)

    def test_filtering_by_categories_success(self):
        response = self.client.get(path=reverse(viewname="v2:rbac:role-list"), data={"categories": "cluster_one"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 44)

    def test_list_object_candidates_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:rbac:role-object-candidates", kwargs={"pk": self.cluster_config_role.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["cluster"]), 2)
        self.assertEqual(response.json()["cluster"][0]["name"], self.cluster_1.name)
        self.assertEqual(response.json()["cluster"][1]["name"], self.cluster_2.name)
