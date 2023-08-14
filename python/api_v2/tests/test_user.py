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

from copy import deepcopy

from api_v2.rbac.users.constants import UserStatusChoices, UserTypeChoices
from api_v2.tests.base import BaseAPITestCase
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.timezone import now
from rbac.models import Group, OriginType, User
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


class TestUserAPI(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.group = Group.objects.create(name="test_group")

    def _create_user(self, user_data: dict | None = None) -> Response:
        if user_data is None:
            user_data = {
                "username": "test_user_username",
                "password": "test_user_password",
                "email": "testuser@mail.ru",
            }

        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:user-list"),
            data=user_data,
        )

        return response

    def _grant_permissions(self, user: User) -> None:
        view_user_permission, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(model=User),
            codename=f"view_{User.__name__.lower()}",
        )
        change_user_permission, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(model=User),
            codename=f"change_{User.__name__.lower()}",
        )

        user.user_permissions.add(*(view_user_permission, change_user_permission))

    def test_create_success(self):
        data = {
            "username": "test_user_username",
            "password": "test_user_password",
            "firstName": "test_user_first_name",
            "lastName": "test_user_last_name",
            "groups": [{"id": self.group.pk}],
            "email": "testuser@mail.ru",
            "isSuperuser": False,
        }
        response: Response = self._create_user(user_data=data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        del data["password"]
        actual_data = {field: response.json()[field] for field in data}
        actual_data["groups"] = [{"id": group["id"]} for group in response.json()["groups"]]
        self.assertDictEqual(actual_data, data)

        only_required_data = {
            "username": "test_user_username_1",
            "password": "test_user_password_1",
        }
        response: Response = self._create_user(user_data=only_required_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_create_wrong_data_fail(self):
        required_data = {
            "username": "test_user_username",
            "password": "test_user_password",
        }
        for field in required_data:
            wrong_data = deepcopy(required_data)
            del wrong_data[field]
            response: Response = self._create_user(user_data=wrong_data)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_retrieve_success(self):
        user = self.create_user()
        response: Response = self.client.get(path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_retrieve_not_exists_fail(self):
        wrong_pk = self.get_non_existent_pk(model=User)
        response: Response = self.client.get(path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": wrong_pk}))
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_update_by_superuser_success(self):
        new_group = Group.objects.create(name="new_group")
        user_data = {
            "username": "test_user",
            "password": "test_user_password",
            "email": "test_user@mail.ru",
            "first_name": "test_user_first_name",
            "last_name": "test_user_last_name",
            "profile": "",
        }
        user = self.create_user(user_data=user_data)
        data = {
            "password": "newtestpassword",
            "firstName": "newtestfn",
            "lastName": "newtestln",
            "email": "newtest@mail.ru",
            "isSuperuser": True,
            "groups": [{"id": new_group.pk}],
        }

        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        patch_response = response.json()

        new_password = data["password"]
        del data["password"]
        actual_data = {field: patch_response[field] for field in data}
        actual_data["groups"] = [{"id": group["id"]} for group in patch_response["groups"]]
        self.assertDictEqual(data, actual_data)

        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.check_password(raw_password=user_data["password"]))
        self.assertTrue(user.check_password(raw_password=new_password))

    def test_update_self_by_regular_user_success(self):
        user_data = {
            "username": "test_user",
            "password": "test_user_password",
            "email": "test_user@mail.ru",
            "first_name": "test_user_first_name",
            "last_name": "test_user_last_name",
            "profile": "",
        }
        user = self.create_user(user_data=user_data)
        self._grant_permissions(user=user)

        data = {
            "password": "newtestpassword",
            "current_password": user_data["password"],
        }

        self.client.login(**user_data)
        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        user.refresh_from_db()
        self.assertFalse(user.check_password(raw_password=user_data["password"]))
        self.assertTrue(user.check_password(raw_password=data["password"]))

    def test_update_not_self_by_regular_user_fail(self):
        user_datas = [
            {
                "username": "test_user",
                "password": "test_user_password",
                "email": "test_user@mail.ru",
                "first_name": "test_user_first_name",
                "last_name": "test_user_last_name",
                "profile": "",
            },
            {
                "username": "test_user2",
                "password": "test_user2_password",
                "email": "test_user2@mail.ru",
                "first_name": "test_user2_first_name",
                "last_name": "test_user2_last_name",
                "profile": "",
            },
        ]
        for user_data in user_datas:
            self.create_user(user_data=user_data)

        first_user = User.objects.get(username=user_datas[0]["username"])
        second_user = User.objects.get(username=user_datas[1]["username"])

        self._grant_permissions(user=first_user)

        data = {
            "password": "new_test_user2_password",
            "current_password": user_datas[1]["password"],
        }

        self.client.login(**user_datas[0])
        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": second_user.pk}),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        second_user.refresh_from_db()
        self.assertFalse(second_user.check_password(raw_password=data["password"]))
        self.assertTrue(second_user.check_password(raw_password=user_datas[1]["password"]))

    def test_update_self_by_regular_user_wrong_data_fail(self):
        user_data = {
            "username": "test_user",
            "password": "test_user_password",
            "email": "test_user@mail.ru",
            "first_name": "test_user_first_name",
            "last_name": "test_user_last_name",
            "profile": "",
        }

        user = self.create_user(user_data=user_data)

        self._grant_permissions(user=User.objects.get(pk=user.pk))

        wrong_data_no_current_password = {
            "password": "newtestpassword",
            "first_name": "newtestfn",
            "last_name": "newtestln",
            "email": "newtest@mail.ru",
            "is_superuser": True,
        }

        self.client.login(**user_data)
        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}),
            data=wrong_data_no_current_password,
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_delete_success(self):
        user = self.create_user()

        response: Response = self.client.delete(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertIsNone(response.data)

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(pk=user.pk)

    def test_delete_built_in_fail(self):
        user = self.create_user()
        user.built_in = True
        user.save(update_fields=["built_in"])

        response: Response = self.client.delete(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}),
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_block_success(self):
        user = self.create_user()

        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:user-block", kwargs={"pk": user.pk}),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNone(response.data)

        response: Response = self.client.get(path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}))
        self.assertEqual(response.json()["status"], "BLOCKED")

        user.refresh_from_db()
        self.assertIsNotNone(user.blocked_at)

    def test_block_built_in_fail(self):
        user = self.create_user()
        user.built_in = True
        user.save(update_fields=["built_in"])

        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:user-block", kwargs={"pk": user.pk}),
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_unblock_success(self):
        user = self.create_user()
        user.blocked_at = now()
        user.save(update_fields=["blocked_at"])

        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": user.pk}),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNone(response.data)

        response: Response = self.client.get(path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}))
        self.assertEqual(response.json()["status"], "ACTIVE")

        user.refresh_from_db()
        self.assertIsNone(user.blocked_at)

    def test_unblock_built_in_fail(self):
        user = self.create_user()
        user.built_in = True
        user.save(update_fields=["built_in"])

        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": user.pk}),
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_ordering_success(self):
        user_data = [
            {
                "username": "username1",
                "password": "username1password",
                "email": "username1@mail.ru",
                "first_name": "username1_first_name",
                "last_name": "username1_last_name",
                "profile": "",
            },
            {
                "username": "username2",
                "password": "username2password",
                "email": "username2@mail.ru",
                "first_name": "username2_first_name",
                "last_name": "username2_last_name",
                "profile": "",
            },
            {
                "username": "username3",
                "password": "username3password",
                "email": "username3@mail.ru",
                "first_name": "username3_first_name",
                "last_name": "username3_last_name",
                "profile": "",
            },
        ]
        for data in user_data:
            self.create_user(user_data=data)

        response: Response = self.client.get(path=reverse(viewname="v2:rbac:user-list"), data={"ordering": "-username"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        response_usernames = [user["username"] for user in response.json()["results"]]
        db_usernames = list(User.objects.order_by("-username").values_list("username", flat=True))
        self.assertListEqual(response_usernames, db_usernames)

    def test_ordering_wrong_params_fail(self):
        response: Response = self.client.get(path=reverse(viewname="v2:rbac:user-list"), data={"ordering": "param"})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_filtering_by_username_success(self):
        user_data = [
            {
                "username": "username1",
                "password": "username1password",
                "email": "username1@mail.ru",
                "first_name": "username1_first_name",
                "last_name": "username1_last_name",
                "profile": "",
            },
            {
                "username": "username2",
                "password": "username2password",
                "email": "username2@mail.ru",
                "first_name": "username2_first_name",
                "last_name": "username2_last_name",
                "profile": "",
            },
        ]
        for data in user_data:
            self.create_user(user_data=data)

        response: Response = self.client.get(path=reverse(viewname="v2:rbac:user-list"), data={"username": "username1"})
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["username"], "username1")

    def test_filtering_by_status_success(self):
        user_data = [
            {
                "username": "username1",
                "password": "username1password",
                "email": "username1@mail.ru",
                "first_name": "username1_first_name",
                "last_name": "username1_last_name",
                "profile": "",
            },
            {
                "username": "username2",
                "password": "username2password",
                "email": "username2@mail.ru",
                "first_name": "username2_first_name",
                "last_name": "username2_last_name",
                "profile": "",
            },
        ]
        for data in user_data:
            self.create_user(user_data=data)

        target_user = User.objects.get(username="username2")
        target_user.blocked_at = now()
        target_user.save(update_fields=["blocked_at"])

        response: Response = self.client.get(
            path=reverse(viewname="v2:rbac:user-list"), data={"status": UserStatusChoices.BLOCKED.value}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["username"], target_user.username)

    def test_filtering_by_type_success(self):
        user_data = [
            {
                "username": "username1",
                "password": "username1password",
                "email": "username1@mail.ru",
                "first_name": "username1_first_name",
                "last_name": "username1_last_name",
                "profile": "",
            },
            {
                "username": "username2",
                "password": "username2password",
                "email": "username2@mail.ru",
                "first_name": "username2_first_name",
                "last_name": "username2_last_name",
                "profile": "",
            },
        ]
        for data in user_data:
            self.create_user(user_data=data)

        target_user = User.objects.get(username="username2")
        target_user.type = OriginType.LDAP
        target_user.save(update_fields=["type"])

        response: Response = self.client.get(
            path=reverse(viewname="v2:rbac:user-list"), data={"type": UserTypeChoices.LDAP.value}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["username"], target_user.username)
