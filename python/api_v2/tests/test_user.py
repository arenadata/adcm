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

import datetime

from adcm.tests.client import ADCMTestClient
from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from rbac.models import Group, OriginType, Role, User
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
import pytz

from api_v2.rbac.user.constants import UserTypeChoices
from api_v2.rbac.user.serializers import UserCreateSerializer, UserUpdateSerializer
from api_v2.tests.base import BaseAPITestCase


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
        response = (self.client.v2 / "rbac" / "users").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
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
                    "blockingReason",
                ]
            ),
        )

    def test_list_no_perms_empty_list_success(self) -> None:
        self.create_user(user_data={"username": "test_user", "password": "test_user_password"})
        self.client.login(username="test_user", password="test_user_password")

        response = (self.client.v2 / "rbac" / "users").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)
        self.assertEqual(len(response.json()["results"]), 0)

    def test_retrieve_no_perms_not_found_fail(self) -> None:
        user = self.create_user(user_data={"username": "test_user", "password": "test_user_password"})
        self.client.login(username="test_user", password="test_user_password")

        response = self.client.v2[user].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_create_success(self):
        response = (self.client.v2 / "rbac" / "users").post(
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
        data = response.json()
        self.assertEqual(data["firstName"], "test_user_first_name")
        self.assertEqual(data["lastName"], "test_user_last_name")
        self.assertFalse(data["isSuperUser"])
        self.assertEqual(user.groups.count(), 1)
        self.assertEqual(data["groups"][0]["displayName"], self.group.display_name)

    def test_create_required_fields_success(self):
        response = (self.client.v2 / "rbac" / "users").post(
            data={"username": "test_user_username_1", "password": "test_user_password_1"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="test_user_username_1").exists())

    def test_create_required_fields_fail(self):
        response = (self.client.v2 / "rbac" / "users").post(data={"username": "test_user_username"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "password - This field is required.;", "level": "error"}
        )

    def test_create_password_does_not_meet_requirements_fail(self) -> None:
        response = (self.client.v2 / "rbac" / "users").post(data={"username": "test_user_username", "password": "1"})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_PASSWORD_ERROR")

        response = (self.client.v2 / "rbac" / "users").post(
            data={"username": "test_user_username", "password": "1" * 1000}
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_PASSWORD_ERROR")

    def test_create_taken_email_fail(self) -> None:
        email = "em@ai.il"

        response = (self.client.v2 / "rbac" / "users").post(
            data={"username": "test_user_username_1", "password": "test_user_password_1", "email": email},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = (self.client.v2 / "rbac" / "users").post(
            data={"username": "test_user_username_2", "password": "test_user_password_1", "email": email},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_CREATE_ERROR")
        self.assertEqual(response.json()["desc"], "User with the same email already exist")

    def test_create_taken_username_fail(self) -> None:
        username = "cooluserisbest"

        response = (self.client.v2 / "rbac" / "users").post(
            data={"username": username, "password": "test_user_password_1"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = (self.client.v2 / "rbac" / "users").post(
            data={"username": username, "password": "test_user_password_2"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_CREATE_ERROR")
        self.assertEqual(response.json()["desc"], "User with the same username already exist")

    def test_create_empty_email_success(self) -> None:
        email = ""

        response = (self.client.v2 / "rbac" / "users").post(
            data={"username": "test_user_username_1", "password": "test_user_password_1", "email": email},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = (self.client.v2 / "rbac" / "users").post(
            data={"username": "test_user_username_2", "password": "test_user_password_1", "email": email},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_permissions_granted_on_user_creation_with_group_success(self) -> None:
        creds = {"username": "test_user_username", "password": "test_user_password"}
        policy_create(name="ADCM User group", role=Role.objects.get(name="ADCM User"), group=[self.group])

        response = (self.client.v2 / "rbac" / "users").post(
            data={**creds, "groups": [self.group.pk]},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.client.login(**creds)

        response = self.client.v2[self.cluster_1].get()

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_retrieve_success(self):
        user = self.create_user()

        response = self.client.v2[user].get()

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
                    "blockingReason",
                ]
            ),
        )

        self.assertEqual(response.json()["id"], user.pk)

    def test_listfield_create_update_serializers_group_success(self):
        user = self.create_user(
            user_data={"username": "user", "password": "test_password1", "groups": [{"id": self.group.pk}]}
        )

        try:
            UserUpdateSerializer().to_representation(user)
            UserCreateSerializer().to_representation(user)
        except TypeError:
            self.fail("The exception is raised - ListField fails to represent list of Group objects")

    def test_retrieve_not_found_fail(self):
        wrong_pk = self.get_non_existent_pk(model=User)

        response = (self.client.v2 / "rbac" / "users" / wrong_pk).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_update_by_superuser_success(self):
        group = Group.objects.create(name="group")
        user = self.create_user(user_data={"username": "test_user", "password": "test_user_password"})

        response = self.client.v2[user].patch(
            data={
                "password": "newtestpassword",
                "email": "test_user@mail.ru",
                "firstName": "test_user_first_name",
                "lastName": "test_user_last_name",
                "isSuperUser": True,
                "groups": [group.pk],
            }
        )

        user.refresh_from_db()

        data = response.json()

        expected_group_data = {"id": group.pk, "name": group.name, "displayName": group.display_name}

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertFalse(user.check_password(raw_password="test_user_password"))
        self.assertTrue(user.check_password(raw_password="newtestpassword"))
        self.assertEqual(data["email"], "test_user@mail.ru")
        self.assertEqual(data["firstName"], "test_user_first_name")
        self.assertEqual(data["lastName"], "test_user_last_name")
        self.assertTrue(data["isSuperUser"])
        self.assertEqual(len(data["groups"]), 1)
        self.assertDictEqual(data["groups"][0], expected_group_data)

        response = self.client.v2[user].patch(
            data={"lastName": "WholeNewName"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        user.refresh_from_db()
        self.assertEqual(user.username, "test_user")
        self.assertEqual(user.first_name, "test_user_first_name")
        self.assertEqual(user.last_name, "WholeNewName")
        self.assertListEqual(list(user.groups.values_list("id", flat=True)), [group.pk])
        self.assertTrue(data["isSuperUser"])
        self.assertEqual(len(data["groups"]), 1)
        self.assertDictEqual(data["groups"][0], expected_group_data)

    def test_update_no_change_email_success(self) -> None:
        email = "one@em.ail"
        user = self.create_user(user_data={"username": "test_user", "password": "test_user_password", "email": email})

        response = self.client.v2[user].patch(
            data={"email": email, "firstName": "test_user_first_name"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_update_self_by_regular_user_success(self):
        """
        According to business requirements, a user cannot make himself a superuser and add himself to a group
        """

        group = Group.objects.create(name="group")
        user = self.create_user(user_data={"username": "test_user", "password": "test_user_password"})
        self._grant_permissions(user=user)
        self.client.login(username="test_user", password="test_user_password")

        response = self.client.v2[user].patch(
            data={
                "email": "test_user@mail.ru",
                "firstName": "test_user_first_name",
                "lastName": "test_user_last_name",
                "groups": [group.pk],
            }
        )

        user.refresh_from_db()
        data = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(user.check_password(raw_password="test_user_password"))
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
            "email": "new_test_user2@mail.ru",
            "firstName": "new_test_user2_first_name",
            "lastName": "new_test_user2_last_name",
            "groups": [group.pk],
        }
        response = self.client.v2[second_user].patch(data=new_data)
        second_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(second_user.check_password(raw_password="test_user2_password"))
        self.assertEqual(second_user.email, new_data["email"])
        self.assertEqual(second_user.first_name, new_data["firstName"])
        self.assertEqual(second_user.last_name, new_data["lastName"])

        # not superuser can't change this values
        self.assertFalse(second_user.is_superuser)
        self.assertEqual(second_user.groups.count(), 0)

    def test_update_no_permission_fail(self) -> None:
        creds = {"username": "test_user_username", "password": "test_user_password"}
        user = self.create_user(user_data=creds)
        self.client.login(**creds)

        response = self.client.v2[user].patch(data={})

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_update_view_permission_fail(self) -> None:
        creds = {"username": "test_user_username", "password": "test_user_password"}
        user = self.create_user(user_data=creds)
        view_user_permission, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(model=User),
            codename=f"view_{User.__name__.lower()}",
        )
        user.user_permissions.add(view_user_permission)
        self.client.login(**creds)

        response = self.client.v2[user].patch(data={})

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_update_email_taken_fail(self) -> None:
        email = "ta@k.vot"
        self.create_user(user_data={"username": "test_user", "password": "test_user_password", "email": email})
        user_to_change = self.create_user(
            user_data={"username": "test_user_2", "password": "test_user_password", "email": "custom@em.ail"}
        )

        response = self.client.v2[user_to_change].patch(data={"email": email})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_CONFLICT")
        self.assertEqual(response.json()["desc"], "User with the same email already exist")

    def test_update_incorrect_password_fail(self) -> None:
        user = self.create_user(user_data={"username": "test_user", "password": "test_user_password"})

        response = self.client.v2[user].patch(
            data={"password": "1"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_PASSWORD_ERROR")

        response = self.client.v2[user].patch(
            data={"password": "1" * 1000},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_PASSWORD_ERROR")

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

        response = (self.client.v2 / "profile").patch(data={"newPassword": "newtestpassword"})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "USER_PASSWORD_CURRENT_PASSWORD_REQUIRED_ERROR",
                "desc": 'Field "current_password" should be filled and match user current password',
                "level": "error",
            },
        )

    def test_update_ldap_user_fail(self) -> None:
        user = self.create_user(user_data={"username": "somebody", "password": "very_long_veryvery"})
        user.type = OriginType.LDAP
        user.save()

        for field in ("password", "email", "first_name", "last_name"):
            with self.subTest(f"Change {field}"):
                response = self.client.v2[user].patch(
                    data={field: "someval@ui.ie"},
                )

                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertEqual(response.json()["code"], "USER_UPDATE_ERROR")
                self.assertEqual(response.json()["desc"], "LDAP user's information can't be changed")

    def test_update_add_to_ldap_group_fail(self) -> None:
        user = self.create_user(user_data={"username": "somebody", "password": "very_long_veryvery"})
        self.group.type = OriginType.LDAP
        self.group.save()

        response = self.client.v2[user].patch(
            data={"groups": [self.group.pk]},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_UPDATE_ERROR")
        self.assertEqual(response.json()["desc"], "You cannot add user to LDAP group")

    def test_update_removed_from_ldap_group_fail(self) -> None:
        user = self.create_user(user_data={"username": "somebody", "password": "very_long_veryvery"})
        self.group.type = OriginType.LDAP
        self.group.save()
        self.group.user_set.add(user)

        response = self.client.v2[user].patch(
            data={"groups": []},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_UPDATE_ERROR")
        self.assertEqual(response.json()["desc"], "You cannot remove user from original LDAP group")

    def test_update_add_to_non_existing_group_fail(self) -> None:
        user = self.create_user(user_data={"username": "somebody", "password": "very_long_veryvery"})

        response = self.client.v2[user].patch(
            data={"groups": [1000]},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "USER_UPDATE_ERROR")
        self.assertEqual(response.json()["desc"], "Some of groups doesn't exist")

    def test_permissions_updated_on_group_change_success(self) -> None:
        creds = {"username": "test_user_username", "password": "test_user_password"}

        policy_create(
            name="ADCM User group",
            role=role_create(name="Awesome Role", child=[Role.objects.get(name="View users")]),
            group=[self.group],
        )
        group_2 = Group.objects.create(name="test_group_2")
        policy_create(
            name="Cluster Admin",
            role=Role.objects.get(name="Cluster Administrator"),
            object=[self.cluster_1],
            group=[group_2],
        )

        user = self.create_user(user_data={**creds, "groups": [{"id": self.group.pk}]})

        user_client = ADCMTestClient()
        user_client.login(**creds)

        self.assertEqual(
            self.client.v2[user].get().status_code,
            HTTP_200_OK,
        )
        self.assertEqual(
            user_client.v2[self.cluster_1].get().status_code,
            HTTP_404_NOT_FOUND,
        )

        self.client.v2[user].patch(
            data={"groups": [group_2.pk]},
        )
        self.assertEqual(
            user_client.v2[user].get().status_code,
            HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.v2[self.cluster_1].get().status_code,
            HTTP_200_OK,
        )

    def test_adcm_5355_update_remove_from_groups_bug(self) -> None:
        group_2 = Group.objects.create(name="test_group_2")
        user = self.create_user(
            user_data={"username": "somebody", "password": "very_long_veryvery", "groups": [{"id": self.group.pk}]}
        )
        self.assertEqual(user.groups.count(), 1)

        update_path = self.client.v2[user]
        response = update_path.patch(data={"groups": []})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["groups"]), 0)
        user.refresh_from_db()
        self.assertEqual(user.groups.count(), 0)

        response = update_path.patch(data={"groups": [self.group.pk, group_2.pk]})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["groups"]), 2)
        user.refresh_from_db()
        self.assertEqual(user.groups.count(), 2)

        response = update_path.patch(data={"groups": [group_2.pk]})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["groups"]), 1)
        self.assertEqual(response.json()["groups"][0]["id"], group_2.pk)
        user.refresh_from_db()
        self.assertEqual(user.groups.count(), 1)

    def test_delete_success(self):
        user = self.create_user()

        response = self.client.v2[user].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertIsNone(response.data)

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(pk=user.pk)

    def test_delete_built_in_fail(self):
        user = self.create_user()
        user.built_in = True
        user.save(update_fields=["built_in"])

        response = self.client.v2[user].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "USER_DELETE_ERROR", "desc": "Built-in user could not be deleted", "level": "error"},
        )

    def test_ordering_success(self):
        ordering_fields = {
            "id": "id",
            "username": "username",
            "type": "type",
        }

        for model_field, ordering_field in ordering_fields.items():
            with self.subTest(ordering_field=ordering_field):
                response = (self.client.v2 / "rbac" / "users").get(query={"ordering": ordering_field})
                self.assertListEqual(
                    [user[ordering_field] for user in response.json()["results"]],
                    list(
                        User.objects.order_by(model_field)
                        .exclude(username__in=settings.ADCM_HIDDEN_USERS)
                        .values_list(model_field, flat=True)
                    ),
                )

                response = (self.client.v2 / "rbac" / "users").get(query={"ordering": f"-{ordering_field}"})
                self.assertListEqual(
                    [user[ordering_field] for user in response.json()["results"]],
                    list(
                        User.objects.order_by(f"-{model_field}")
                        .exclude(username__in=settings.ADCM_HIDDEN_USERS)
                        .values_list(model_field, flat=True)
                    ),
                )

    def test_ordering_wrong_params_fail(self):
        response = (self.client.v2 / "rbac" / "users").get(query={"ordering": "param"})

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

        response = (self.client.v2 / "rbac" / "users").get(query={"username": "username1"})
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

        target_user1 = User.objects.get(username="username2")
        target_user1.blocked_at = now()
        target_user1.save(update_fields=["blocked_at"])

        target_user2 = User.objects.get(username="username3")
        target_user2.is_active = False
        target_user2.save(update_fields=["is_active"])

        response = (self.client.v2 / "rbac" / "users").get(query={"status": "blocked"})
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 2)
        self.assertEqual(response.json()["results"][0]["username"], target_user1.username)
        self.assertEqual(response.json()["results"][1]["username"], target_user2.username)

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

        response = (self.client.v2 / "rbac" / "users").get(query={"type": UserTypeChoices.LDAP.value})
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["username"], target_user.username)

    def test_adcm_5495_list_users_when_auth_group_has_no_rbac_group_bug(self) -> None:
        user = self.create_user(user_data={"username": "test_user", "password": "test_user_password"})
        # In regular usage it's not the case that there are `auth_group` without corresponding `rbac_group`,
        # but this bug was originated from such situation.
        # Thou it's unclear how's that happened, we shouldn't query
        # and work with such incomplete instances anyway.
        auth_group = AuthGroup.objects.create(name="single_group")
        rbac_group = Group.objects.create(name="single_group [ldap]", type=OriginType.LDAP)
        auth_group.user_set.add(user)
        rbac_group.user_set.add(user)

        response = (self.client.v2 / "rbac" / "users").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()["results"]
        self.assertEqual(len(data), 2)
        user_data = next(entry for entry in data if entry["username"] == user.username)
        self.assertEqual(
            user_data["groups"],
            [{"id": rbac_group.id, "name": rbac_group.name, "displayName": rbac_group.display_name}],
        )


class TestBlockUnblockAPI(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.user = self.create_user(user_data={"username": "someuser", "password": "bestpasseverever"})
        self.admin = User.objects.get(username="admin")

        creds = {"username": "editor", "password": "bestpasseverever"}
        self.user_with_edit = self.create_user(user_data=creds)
        self.user_with_edit.user_permissions.add(
            Permission.objects.get(content_type=ContentType.objects.get_for_model(model=User), codename="view_user")
        )
        self.edit_client = ADCMTestClient()
        self.edit_client.login(**creds)

    def test_retrieve_blocked_by_login_attempts(self) -> None:
        self.user.blocked_at = datetime.datetime.now(tz=pytz.UTC)
        self.user.save()

        response = self.client.v2[self.user].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["blockingReason"], "Brute-force block: failure login attempt limit exceeded")

    def test_retrieve_blocked_manually(self) -> None:
        self.user.is_active = False
        self.user.save()

        response = self.client.v2[self.user].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["blockingReason"], "Unlimited block: manual block by ADCM Administrator")

    def test_retrieve_blocked_both_ways(self) -> None:
        self.user.is_active = False
        self.user.blocked_at = datetime.datetime.now(tz=pytz.UTC)
        self.user.save()

        response = self.client.v2[self.user].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["blockingReason"], "Unlimited block: manual block by ADCM Administrator")

    def test_retrieve_not_blocked(self) -> None:
        self.user.failed_login_attempts = 10
        self.user.save()

        response = self.client.v2[self.user].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["blockingReason"], None)

    def test_block_manually_success(self) -> None:
        response = self.client.v2[self.user, "block"].post(data=None)

        self.assertEqual(response.status_code, HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertIsNone(self.user.blocked_at)
        self.assertFalse(self.user.is_active)

    def test_block_manually_self_fail(self) -> None:
        response = self.client.v2[self.admin, "block"].post(data=None)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["desc"], "You can't block yourself.")

        self.admin.refresh_from_db()
        self.assertIsNone(self.admin.blocked_at)
        self.assertTrue(self.admin.is_active)

    def test_block_not_superuser_fail(self) -> None:
        response = (self.edit_client.v2 / "rbac" / "users" / self.user.pk / "block").post(data=None)

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "You do not have permission to perform this action.")

        self.admin.refresh_from_db()
        self.assertIsNone(self.user.blocked_at)
        self.assertTrue(self.user.is_active)

    def test_block_ldap_user_fail(self) -> None:
        self.user.type = OriginType.LDAP
        self.user.save()

        response = self.client.v2[self.user, "block"].post(data=None)
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["desc"], "You can't block LDAP users.")

    def test_unblock_success(self) -> None:
        self.user.is_active = False
        self.user.blocked_at = datetime.datetime.now(tz=pytz.UTC)
        self.user.failed_login_attempts = 10
        self.user.save()

        response = self.client.v2[self.user, "unblock"].post(data=None)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.blocked_at)
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.failed_login_attempts, 0)

    def test_unblock_ldap_success(self) -> None:
        self.user.is_active = False
        self.user.blocked_at = datetime.datetime.now(tz=pytz.UTC)
        self.user.failed_login_attempts = 10
        self.user.type = OriginType.LDAP
        self.user.save()

        response = self.client.v2[self.user, "unblock"].post(data=None)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNone(self.user.blocked_at)
        self.assertEqual(self.user.failed_login_attempts, 0)

    def test_unblock_not_superuser_fail(self) -> None:
        response = (self.edit_client.v2 / "rbac" / "users" / self.user.pk / "unblock").post(data=None)

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["detail"], "You do not have permission to perform this action.")
