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

from adcm.tests.base import TestUserCreateDTO
from api_v2.tests.base import BaseAPITestCase
from django.contrib.auth.hashers import check_password
from rbac.models import Role, User
from rbac.services import group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rbac.services.user import perform_user_creation
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT
from rest_framework.test import APIClient


class TestUserCreateEdit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.password = "yes" * 5
        create_user_role = role_create(
            name="Create Users",
            display_name="Create Users",
            child=[Role.objects.get(name="Create user", built_in=True)],
        )
        edit_user_role = role_create(
            name="Edit Users",
            display_name="Edit Users",
            child=[Role.objects.get(name="Edit user", built_in=True)],
        )
        creators_group = group.create(name_to_display="Creators")
        editors_group = group.create(name_to_display="Editors")

        self.creator = User.objects.get(
            id=perform_user_creation(
                create_data=TestUserCreateDTO(username="icancreate", password=self.password, is_superuser=False),
                groups=[creators_group.pk],
            )
        )
        self.editor = User.objects.get(
            id=perform_user_creation(
                create_data=TestUserCreateDTO(username="icanedit", password=self.password, is_superuser=False),
                groups=[editors_group.pk],
            )
        )

        self.creator_client = APIClient()
        self.creator_client.login(username="icancreate", password=self.password)
        self.editor_client = APIClient()
        self.editor_client.login(username="icanedit", password=self.password)

        policy_create(name="Creators policy", role=create_user_role, group=[creators_group])
        policy_create(name="Editors policy", role=edit_user_role, group=[editors_group])

        self.new_user_data = {
            "username": "newcooluser",
            "password": "bestpassever",
            "first_name": "Awesome",
            "last_name": "Tiger",
            "email": "difficult@to.me",
        }

    @staticmethod
    def request_create_user(client: APIClient, data: dict) -> Response:
        return client.post(path="/api/v1/rbac/user/", data=data)

    @staticmethod
    def request_edit_user(client: APIClient, user_id: int, data: dict) -> Response:
        return client.patch(path=f"/api/v1/rbac/user/{user_id}/", data=data)

    # Create Restrictions

    def test_create_user_perm_does_not_allow_superuser_creation(self) -> None:
        response = self.request_create_user(
            client=self.creator_client, data=self.new_user_data | {"is_superuser": True}
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["desc"], "You can't create user with ADCM Administrator's rights.")
        self.assertFalse(User.objects.filter(username=self.new_user_data["username"]).exists())

    def test_superuser_can_create_superuser(self) -> None:
        response = self.request_create_user(client=self.client, data=self.new_user_data | {"is_superuser": True})

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        new_user = User.objects.filter(username=self.new_user_data["username"]).first()
        self.assertIsNotNone(new_user)
        self.assertTrue(new_user.is_superuser)

    # Edit Restrictions

    def test_edit_user_perm_does_not_allow_superuser_status_change(self) -> None:
        with self.subTest("Edit Oneself"):
            response = self.request_edit_user(
                client=self.editor_client, user_id=self.editor.pk, data={"is_superuser": True}
            )

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
            self.assertEqual(response.json()["desc"], "You can't grant ADCM Administrator's rights.")
            self.editor.refresh_from_db()
            self.assertFalse(self.editor.is_superuser)

        with self.subTest("Edit Another"):
            response = self.request_edit_user(
                client=self.editor_client, user_id=self.creator.pk, data={"is_superuser": True}
            )

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
            self.assertEqual(response.json()["desc"], "You can't grant ADCM Administrator's rights.")
            self.creator.refresh_from_db()
            self.assertFalse(self.creator.is_superuser)

        with self.subTest("Withdraw"):
            admin = User.objects.get(username="admin")
            response = self.request_edit_user(client=self.editor_client, user_id=admin.pk, data={"is_superuser": False})

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
            self.assertEqual(response.json()["desc"], "You can't withdraw ADCM Administrator's rights.")
            admin.refresh_from_db()
            self.assertTrue(admin.is_superuser)

    def test_edit_user_perm_does_not_allow_changing_password(self) -> None:
        with self.subTest("Changed Password Provided"):
            response = self.request_edit_user(
                client=self.editor_client, user_id=self.creator.pk, data={"password": "newpassgoodandbetter"}
            )

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
            self.assertEqual(response.json()["desc"], "You can't change user's password.")
            self.creator.refresh_from_db()
            check_password(self.password, self.creator.password)

        with self.subTest("Same Password Provided"):
            response = self.request_edit_user(
                client=self.editor_client, user_id=self.creator.pk, data={"password": self.password}
            )

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
            self.assertEqual(response.json()["desc"], "You can't change user's password.")
            self.creator.refresh_from_db()
            check_password(self.password, self.creator.password)

    def test_superuser_can_change_superuser_status_of_another_user(self) -> None:
        with self.subTest("Can Grant"):
            response = self.request_edit_user(client=self.client, user_id=self.editor.pk, data={"is_superuser": True})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.editor.refresh_from_db()
            self.assertTrue(self.editor.is_superuser)

        with self.subTest("Can Withdraw"):
            response = self.request_edit_user(client=self.client, user_id=self.editor.pk, data={"is_superuser": False})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.editor.refresh_from_db()
            self.assertFalse(self.editor.is_superuser)

    def test_superuser_cannot_withdraw_own_superuser_status(self) -> None:
        admin = User.objects.get(username="admin")
        response = self.request_edit_user(client=self.client, user_id=admin.pk, data={"is_superuser": False})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["desc"], "You can't withdraw ADCM Administrator's rights from yourself.")
        admin.refresh_from_db()
        self.assertTrue(admin.is_superuser)
