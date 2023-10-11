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


from api_v2.rbac.user.constants import UserTypeChoices
from api_v2.tests.base import BaseAPITestCase
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.timezone import now
from rbac.models import Group, OriginType, User
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

    def test_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:rbac:user-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)
        self.assertListEqual(
            sorted(response.json()["results"][0].keys()),
            sorted(
                [
                    "id",
                    "username",
                    "firstName",
                    "lastName",
                    "status",
                    "email",
                    "type",
                    "isBuiltIn",
                    "isSuperUser",
                    "groups",
                ]
            ),
        )

    def test_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:user-list"),
            data={
                "username": "test_user_username",
                "password": "test_user_password",
                "firstName": "test_user_first_name",
                "lastName": "test_user_last_name",
                "groups": [self.group.pk],
                "email": "testuser@mail.ru",
                "isSuperuser": False,
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        user = User.objects.filter(username="test_user_username").first()
        self.assertIsNotNone(user)
        self.assertEqual(response.json()["firstName"], "test_user_first_name")
        self.assertEqual(response.json()["lastName"], "test_user_last_name")
        self.assertFalse(response.json()["isSuperUser"])
        self.assertEqual(user.groups.count(), 1)

    def test_create_required_fields_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:user-list"),
            data={"username": "test_user_username_1", "password": "test_user_password_1"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="test_user_username_1").exists())

    def test_create_required_fields_fail(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:user-list"), data={"username": "test_user_username"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "password - This field is required.;", "level": "error"}
        )

    def test_retrieve_success(self):
        user = self.create_user()

        response = self.client.get(path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            sorted(response.json().keys()),
            sorted(
                [
                    "id",
                    "username",
                    "firstName",
                    "lastName",
                    "status",
                    "email",
                    "type",
                    "isBuiltIn",
                    "isSuperUser",
                    "groups",
                ]
            ),
        )

        self.assertEqual(response.json()["id"], user.pk)

    def test_retrieve_not_found_fail(self):
        wrong_pk = self.get_non_existent_pk(model=User)

        response = self.client.get(path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": wrong_pk}))

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_update_by_superuser_success(self):
        group = Group.objects.create(name="group")
        user = self.create_user(user_data={"username": "test_user", "password": "test_user_password"})

        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}),
            data={
                "password": "newtestpassword",
                "email": "test_user@mail.ru",
                "firstName": "test_user_first_name",
                "lastName": "test_user_last_name",
                "isSuperUser": True,
                "groups": [group.pk],
            },
        )

        user.refresh_from_db()

        data = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertFalse(user.check_password(raw_password="test_user_password"))
        self.assertTrue(user.check_password(raw_password="newtestpassword"))
        self.assertEqual(data["email"], "test_user@mail.ru")
        self.assertEqual(data["firstName"], "test_user_first_name")
        self.assertEqual(data["lastName"], "test_user_last_name")
        self.assertTrue(data["isSuperUser"])
        self.assertEqual(len(data["groups"]), 1)
        self.assertDictEqual(data["groups"][0], {"id": group.pk, "name": group.name, "displayName": group.display_name})

    def test_update_self_by_regular_user_success(self):
        """
        According to business requirements, a user cannot make himself a super user and add himself to a group
        """

        group = Group.objects.create(name="group")
        user = self.create_user(user_data={"username": "test_user", "password": "test_user_password"})
        self._grant_permissions(user=user)
        self.client.login(username="test_user", password="test_user_password")

        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}),
            data={
                "password": "newtestpassword",
                "email": "test_user@mail.ru",
                "firstName": "test_user_first_name",
                "lastName": "test_user_last_name",
                "isSuperUser": True,
                "groups": [group.pk],
            },
        )

        user.refresh_from_db()
        data = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertFalse(user.check_password(raw_password="test_user_password"))
        self.assertTrue(user.check_password(raw_password="newtestpassword"))
        self.assertEqual(data["email"], "test_user@mail.ru")
        self.assertEqual(data["firstName"], "test_user_first_name")
        self.assertEqual(data["lastName"], "test_user_last_name")
        self.assertFalse(data["isSuperUser"])
        self.assertEqual(len(data["groups"]), 0)

    def test_update_not_self_by_regular_user_success(self):
        group = Group.objects.create(name="group")
        first_user = self.create_user(user_data={"username": "test_user", "password": "test_user_password"})
        second_user = self.create_user(
            user_data={
                "username": "test_user2",
                "password": "test_user2_password",
                "email": "test_user2@mail.ru",
                "first_name": "test_user2_first_name",
                "last_name": "test_user2_last_name",
            }
        )
        self._grant_permissions(user=first_user)
        self.client.login(username="test_user", password="test_user_password")

        new_data = {
            "password": "newtestuser2password",
            "email": "new_test_user2@mail.ru",
            "firstName": "new_test_user2_first_name",
            "lastName": "new_test_user2_last_name",
            "isSuperUser": True,
            "groups": [group.pk],
        }
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": second_user.pk}),
            data=new_data,
        )
        second_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(second_user.check_password(raw_password=new_data["password"]))
        self.assertFalse(second_user.check_password(raw_password="test_user2_password"))
        self.assertEqual(second_user.email, new_data["email"])
        self.assertEqual(second_user.first_name, new_data["firstName"])
        self.assertEqual(second_user.last_name, new_data["lastName"])

        # not superuser can't change this values
        self.assertFalse(second_user.is_superuser)
        self.assertEqual(second_user.groups.count(), 0)

    def test_update_password_self_by_profile_fail(self):
        user_data = {
            "username": "test_user",
            "password": "test_user_password",
            "email": "test_user@mail.ru",
            "first_name": "test_user_first_name",
            "last_name": "test_user_last_name",
        }

        user = self.create_user(user_data=user_data)

        self._grant_permissions(user=user)

        self.client.login(username="test_user", password="test_user_password")

        response = self.client.put(path=reverse(viewname="v2:adcm:profile"), data={"newPassword": "newtestpassword"})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "USER_PASSWORD_CURRENT_PASSWORD_REQUIRED_ERROR",
                "desc": 'Field "current_password" should be filled and match user current password',
                "level": "error",
            },
        )

    def test_delete_success(self):
        user = self.create_user()

        response = self.client.delete(
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

        response = self.client.delete(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": user.pk}),
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "USER_DELETE_ERROR", "desc": "Built-in user could not be deleted", "level": "error"},
        )

    def test_unblock_success(self):
        user = self.create_user()
        user.blocked_at = now()
        user.failed_login_attempts = 5
        user.save(update_fields=["blocked_at", "failed_login_attempts"])

        response = self.client.post(
            path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": user.pk}),
        )

        user.refresh_from_db()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNone(response.data)
        self.assertIsNone(user.blocked_at)
        self.assertEqual(user.failed_login_attempts, 0)

    def test_unblock_built_in_fail(self):
        user = self.create_user()
        user.built_in = True
        user.save(update_fields=["built_in"])

        response = self.client.post(
            path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": user.pk}),
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "USER_BLOCK_ERROR", "desc": "Built-in user could not be blocked", "level": "error"},
        )

    def test_ordering_success(self):
        user_data = [
            {
                "username": "username1",
                "password": "username1password",
                "email": "username1@mail.ru",
                "first_name": "username1_first_name",
                "last_name": "username1_last_name",
            },
            {
                "username": "username2",
                "password": "username2password",
                "email": "username2@mail.ru",
                "first_name": "username2_first_name",
                "last_name": "username2_last_name",
            },
            {
                "username": "username3",
                "password": "username3password",
                "email": "username3@mail.ru",
                "first_name": "username3_first_name",
                "last_name": "username3_last_name",
            },
        ]
        for data in user_data:
            self.create_user(user_data=data)

        response = self.client.get(path=reverse(viewname="v2:rbac:user-list"), data={"ordering": "-username"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        response_usernames = [user["username"] for user in response.json()["results"]]
        db_usernames = list(User.objects.order_by("-username").values_list("username", flat=True))
        self.assertListEqual(response_usernames, db_usernames)

    def test_ordering_wrong_params_fail(self):
        response = self.client.get(path=reverse(viewname="v2:rbac:user-list"), data={"ordering": "param"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BAD_REQUEST",
                "desc": "ordering - Select a valid choice. param is not one of the available choices.;",
                "level": "error",
            },
        )

    def test_filtering_by_username_success(self):
        user_data = [
            {
                "username": "username1",
                "password": "username1password",
                "email": "username1@mail.ru",
                "first_name": "username1_first_name",
                "last_name": "username1_last_name",
            },
            {
                "username": "username2",
                "password": "username2password",
                "email": "username2@mail.ru",
                "first_name": "username2_first_name",
                "last_name": "username2_last_name",
            },
        ]
        for data in user_data:
            self.create_user(user_data=data)

        response = self.client.get(path=reverse(viewname="v2:rbac:user-list"), data={"username": "username1"})
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
            },
            {
                "username": "username2",
                "password": "username2password",
                "email": "username2@mail.ru",
                "first_name": "username2_first_name",
                "last_name": "username2_last_name",
            },
        ]
        for data in user_data:
            self.create_user(user_data=data)

        target_user = User.objects.get(username="username2")
        target_user.blocked_at = now()
        target_user.save(update_fields=["blocked_at"])

        response = self.client.get(path=reverse(viewname="v2:rbac:user-list"), data={"status": "blocked"})
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
            },
            {
                "username": "username2",
                "password": "username2password",
                "email": "username2@mail.ru",
                "first_name": "username2_first_name",
                "last_name": "username2_last_name",
            },
        ]
        for data in user_data:
            self.create_user(user_data=data)

        target_user = User.objects.get(username="username2")
        target_user.type = OriginType.LDAP
        target_user.save(update_fields=["type"])

        response = self.client.get(
            path=reverse(viewname="v2:rbac:user-list"), data={"type": UserTypeChoices.LDAP.value}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["username"], target_user.username)
