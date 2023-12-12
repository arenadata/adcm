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
from rbac.models import Group, Policy, Role
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)


class TestPolicy(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.remove_hostprovider_role = role_create(
            name="Remove Host-Provider",
            display_name="Remove Host-Provider",
            child=[Role.objects.get(name="Remove provider", built_in=True)],
        )
        self.create_user_role = role_create(
            name="Create Users",
            display_name="Create Users",
            child=[Role.objects.get(name="Create user", built_in=True)],
        )

        self.group_1 = Group.objects.create(name="test_local_group_1")
        self.group_2 = Group.objects.create(name="test_local_group_2")

        self.remove_hostprovider_policy = policy_create(
            name="Awesome Policy", role=self.remove_hostprovider_role, group=[self.group_1], object=[self.provider]
        )
        self.create_user_policy = policy_create(
            name="Create User Policy", role=self.create_user_role, group=[self.group_1, self.group_2], object=[]
        )

    def test_list_policy_success(self) -> None:
        response = self.client.get(path=reverse(viewname="v2:rbac:policy-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertIn("results", data)
        policies = data["results"]
        self.assertEqual(len(policies), 2)
        self.assertTrue(all(set(policy).issuperset({"id", "name", "objects", "groups"}) for policy in policies))

    def test_retrieve_policy_success(self) -> None:
        response = self.client.get(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.create_user_policy.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data).issuperset({"id", "objects", "groups", "role"}))
        self.assertListEqual(data["objects"], [])
        self.assertEqual(
            data["role"],
            {
                "id": self.create_user_role.pk,
                "name": self.create_user_role.name,
                "displayName": self.create_user_role.display_name,
            },
        )
        self.assertListEqual(
            sorted(data["groups"], key=lambda item: item["id"]),
            sorted(
                (
                    {"id": group.pk, "name": group.name, "displayName": group.display_name}
                    for group in (self.group_1, self.group_2)
                ),
                key=lambda item: item["id"],
            ),
        )

    def test_create_parametrized_policy_only_required_fields_success(self) -> None:
        response = self.client.post(
            path=reverse(viewname="v2:rbac:policy-list"),
            data={
                "name": "New Policy",
                "role": {"id": self.remove_hostprovider_role.pk},
                "objects": [{"id": self.provider.pk, "type": "provider"}],
                "groups": [self.group_1.pk],
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(set(data).issuperset({"id", "objects", "groups"}))
        self.assertTrue(Policy.objects.filter(pk=data["id"]).exists())
        self.assertEqual(
            data["objects"],
            [
                {
                    "id": self.provider.pk,
                    "type": "provider",
                    "name": self.provider.name,
                    "displayName": self.provider.display_name,
                }
            ],
        )
        self.assertEqual(
            data["groups"],
            [{"id": self.group_1.pk, "name": self.group_1.name, "displayName": self.group_1.display_name}],
        )

    def test_update_policy_every_field_success(self) -> None:
        new_data = {
            "name": "Updated name",
            "role": {"id": self.create_user_role.pk},
            "objects": [],
            "groups": [self.group_2.pk],
        }
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.remove_hostprovider_policy.pk}),
            data=new_data,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data).issuperset({"id", "objects", "groups"}))
        self.assertEqual(data["id"], self.remove_hostprovider_policy.pk)
        self.assertListEqual(data["objects"], [])
        self.assertEqual(
            data["groups"],
            [{"id": self.group_2.pk, "name": self.group_2.name, "displayName": self.group_2.display_name}],
        )

    def test_delete_policy_success(self) -> None:
        response = self.client.delete(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.create_user_policy.pk})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Policy.objects.filter(pk=self.create_user_policy.pk).exists())

    def test_create_policy_no_group_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:policy-list"),
            data={
                "name": "test_policy_new",
                "description": "description",
                "role": self.create_user_role.pk,
                "objects": [{"type": "cluster", "id": self.cluster_1.pk}],
            },
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_update_policy_no_operation_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.create_user_policy.pk}),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_update_policy_wrong_object_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.create_user_policy.pk}),
            data={"objects": [{"type": "role", "id": self.create_user_role.pk}]},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_adcm_5103_policy_ordering_success(self) -> None:
        for name in ("Test", "Best", "Good", "Class"):
            policy_create(name=name, role=self.create_user_role, group=[self.group_1], object=[])
        response = self.client.get(path=reverse(viewname="v2:rbac:policy-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        policies = [p["name"] for p in response.json()["results"]]
        self.assertEqual(len(policies), 6)
        self.assertEqual(policies, ["Awesome Policy", "Best", "Class", "Create User Policy", "Good", "Test"])
