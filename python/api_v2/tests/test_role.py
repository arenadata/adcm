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
from rbac.models import Role, RoleTypes
from rbac.services.role import role_create
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)


class TestRole(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

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
        self.child = Role.objects.create(
            name="test_child_role",
            display_name="test_child_role",
            type=RoleTypes.BUSINESS,
        )
        self.child_2 = Role.objects.create(
            name="test_child_role_2",
            display_name="test_child_role_2",
            type=RoleTypes.BUSINESS,
        )

    def test_retrieve_not_found_fail(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:rbac:role-detail",
                kwargs={"pk": self.mm_role_cluster.pk + 10},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:rbac:role-detail",
                kwargs={"pk": self.mm_role_cluster.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.mm_role_cluster.pk)

    def test_list_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:rbac:role-list",
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertGreater(len(response.json()["results"]), 1)

    def test_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:role-list"),
            data={
                "name": "test",
                "display_name": "test",
                "children": [{"id": self.child.pk}],
            },
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_update_success(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.mm_role_host.pk}),
            data={
                "name": self.mm_role_host.name + "__changed",
                "display_name": "new name",
                "children": [{"id": self.child_2.pk}],
            },
        )
        updated_role = Role.objects.filter(pk=self.mm_role_host.pk).last()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(updated_role.display_name, "new name")
        self.assertEqual(updated_role.name, self.mm_role_host.name)
        self.assertEqual(list(updated_role.child.all()), list(Role.objects.filter(pk=self.child_2.pk)))

    def test_delete_success(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.mm_role_host.pk}),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertIsNone(Role.objects.filter(pk=self.mm_role_host.pk).last())

    def test_ordering_success(self):
        limit = 10

        response: Response = self.client.get(
            path=reverse(
                viewname="v2:rbac:role-list",
            ),
            data={"ordering": "-name", "limit": limit},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response_names = [role_data["displayName"] for role_data in response.json()["results"]]
        db_names = [role.display_name for role in Role.objects.order_by("-display_name")[:limit]]
        self.assertListEqual(response_names, db_names)

    def test_filtering_success(self):
        filter_name = "cReAtE"

        response: Response = self.client.get(
            path=reverse(
                viewname="v2:rbac:role-list",
            ),
            data={"name": filter_name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response_pks = [role_data["id"] for role_data in response.json()["results"]]
        db_pks = [role.pk for role in Role.objects.filter(display_name__icontains=filter_name)]
        self.assertListEqual(response_pks, db_pks)
