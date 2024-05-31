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

from rbac.models import Group, OriginType
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)

from api_v2.tests.base import BaseAPITestCase


class TestGroupAPI(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.group_local = Group.objects.create(name="test_local_group")
        self.group_ldap = Group.objects.create(name="test_ldap_group", type=OriginType.LDAP)

    def test_list_success(self):
        response: Response = (self.client.v2 / "rbac" / "groups").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_list_no_permissions_success(self):
        user_credentials = {"username": "test_user", "password": "test_user_password"}
        user_create_data = {
            "email": "testuser@mail.ru",
            "first_name": "test_user_first_name",
            "last_name": "test_user_last_name",
            "profile": "",
            **user_credentials,
        }

        self.create_user(user_data=user_create_data)
        self.client.login(**user_credentials)

        response: Response = (self.client.v2 / "rbac" / "groups").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_create_required_fields_success(self):
        response: Response = (self.client.v2 / "rbac" / "groups").post(data={"display_name": "new group name"})

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(Group.objects.count(), 3)

        group = Group.objects.order_by("pk").last()
        self.assertEqual(group.display_name, "new group name")
        self.assertEqual(group.description, "")
        self.assertListEqual(list(group.user_set.all()), [])

    def test_create_with_user_success(self):
        new_user = self.create_user()
        create_data = {"display_name": "new group name", "description": "new group description", "users": [new_user.pk]}

        response: Response = (self.client.v2 / "rbac" / "groups").post(data=create_data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(Group.objects.count(), 3)
        self.assertIn(new_user.pk, Group.objects.get(pk=response.json()["id"]).user_set.values_list("id", flat=True))

    def test_update_success(self):
        new_user = self.create_user()
        update_data = {
            "display_name": "new display name",
            "description": "new description",
            "users": [new_user.pk],
        }

        response: Response = self.client.v2[self.group_local].patch(data=update_data)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.group_local.refresh_from_db()
        self.assertEqual(self.group_local.display_name, update_data["display_name"])
        self.assertEqual(self.group_local.description, update_data["description"])
        self.assertListEqual(list(self.group_local.user_set.values_list("id", flat=True)), update_data["users"])

        response: Response = self.client.v2[self.group_local].patch(data={"display_name": "new_display name"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.group_local.refresh_from_db()
        self.assertEqual(self.group_local.display_name, "new_display name")
        self.assertEqual(self.group_local.description, update_data["description"])
        self.assertListEqual(list(self.group_local.user_set.values_list("id", flat=True)), update_data["users"])

    def test_delete_success(self):
        group_ldap_pk = self.group_ldap.pk
        response: Response = self.client.v2[self.group_ldap].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(pk=group_ldap_pk)

    def test_ordering_by_name_success(self):
        response: Response = (self.client.v2 / "rbac" / "groups").get(query={"ordering": "displayName"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            [group["displayName"] for group in response.json()["results"]],
            [group.display_name for group in Group.objects.order_by("name")],
        )

        response: Response = (self.client.v2 / "rbac" / "groups").get(query={"ordering": "-displayName"})
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            [group["displayName"] for group in response.json()["results"]],
            [group.display_name for group in Group.objects.order_by("-name")],
        )

    def test_filtering_by_display_name_success(self):
        response: Response = (self.client.v2 / "rbac" / "groups").get(query={"displayName": "nonexistentname"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

        response: Response = (self.client.v2 / "rbac" / "groups").get(query={"displayName": "_lDaP_"})
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filtering_by_type_success(self):
        response: Response = (self.client.v2 / "rbac" / "groups").get(query={"type": "local"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filtering_by_wrong_type_fail(self):
        response: Response = (self.client.v2 / "rbac" / "groups").get(query={"type": "wrong-group-type"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_update_add_remove_users_success(self) -> None:
        group = Group.objects.create(name="test_group_2")
        user_1 = self.create_user(
            user_data={"username": "somebody", "password": "very_long_veryvery", "groups": [{"id": group.pk}]}
        )
        user_2 = self.create_user(user_data={"username": "somebody22", "password": "very_long_veryvery", "groups": []})
        self.assertEqual(group.user_set.count(), 1)

        update_path = self.client.v2[group].path
        response = self.client.patch(path=update_path, data={"users": []})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["users"]), 0)

        response = self.client.patch(path=update_path, data={"users": [user_1.pk, user_2.pk]})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["users"]), 2)

        response = self.client.patch(path=update_path, data={"users": [user_2.pk]})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["users"]), 1)
        self.assertEqual(response.json()["users"][0]["id"], user_2.pk)
