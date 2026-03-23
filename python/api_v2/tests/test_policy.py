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

from rbac.models import Group, Policy, Role
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)
from tests.suites import ADCMDjangoAPISuite


class TestPolicy(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.remove_provider_role = role_create(
            name="Remove Host-Provider",
            display_name="Remove Host-Provider",
            child=[Role.objects.get(name="Remove provider", built_in=True)],
        )
        cls.create_user_role = role_create(
            name="Create Users",
            display_name="Create Users",
            child=[Role.objects.get(name="Create user", built_in=True)],
        )

        cls.group_1 = Group.objects.create(name="test_local_group_1")
        cls.group_2 = Group.objects.create(name="test_local_group_2")

        cls.remove_provider_policy = policy_create(
            name="Awesome Policy",
            role=cls.remove_provider_role,
            group=[cls.group_1],
            object=[cls.provider],
            description="first description",
        )
        cls.create_user_policy = policy_create(
            name="Create User Policy",
            role=cls.create_user_role,
            group=[cls.group_1, cls.group_2],
            object=[],
            description="second description",
        )

    def test_list_policy_success(self) -> None:
        response = (self.client.v2 / "rbac" / "policies").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertIn("results", data)
        policies = data["results"]
        self.assertEqual(len(policies), 2)
        self.assertTrue(all(set(policy).issuperset({"id", "name", "objects", "groups"}) for policy in policies))

    def test_retrieve_policy_success(self) -> None:
        response = self.client.v2[self.create_user_policy].get()

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
        response = (self.client.v2 / "rbac" / "policies").post(
            data={
                "name": "New Policy",
                "role": {"id": self.remove_provider_role.pk},
                "objects": [{"id": self.provider.pk, "type": "provider"}],
                "groups": [self.group_1.pk],
            }
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
                    "parentId": None,
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
        response = self.client.v2[self.remove_provider_policy].patch(data=new_data)

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data).issuperset({"id", "objects", "groups"}))
        self.assertEqual(data["id"], self.remove_provider_policy.pk)
        self.assertListEqual(data["objects"], [])
        self.assertEqual(
            data["groups"],
            [{"id": self.group_2.pk, "name": self.group_2.name, "displayName": self.group_2.display_name}],
        )

    def test_delete_policy_success(self) -> None:
        response = self.client.v2[self.create_user_policy].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Policy.objects.filter(pk=self.create_user_policy.pk).exists())

    def test_create_policy_no_group_fail(self):
        response = (self.client.v2 / "rbac" / "policies").post(
            data={
                "name": "test_policy_new",
                "description": "description",
                "role": self.create_user_role.pk,
                "objects": [{"type": "cluster", "id": self.cluster_1.pk}],
            }
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_update_policy_no_operation_success(self):
        response = self.client.v2[self.create_user_policy].patch(
            data={},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_update_policy_wrong_object_fail(self):
        response = self.client.v2[self.create_user_policy].patch(
            data={"objects": [{"type": "role", "id": self.create_user_role.pk}]}
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_adcm_5103_policy_ordering_success(self) -> None:
        for name in ("Test", "Best", "Good", "Class"):
            policy_create(name=name, role=self.create_user_role, group=[self.group_1], object=[])
        response = (self.client.v2 / "rbac" / "policies").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        policies = [p["name"] for p in response.json()["results"]]
        self.assertEqual(len(policies), 6)
        self.assertEqual(policies, ["Awesome Policy", "Best", "Class", "Create User Policy", "Good", "Test"])

    def test_adcm_7787_policy_objects_response(self):
        service_2, service_3, service_6 = (
            self.add_services_to_cluster(
                service_names=["service_2", "service_3_manual_add", "service_6_delete_with_action"],
                cluster=self.cluster_1,
            )
            .order_by("prototype__name")
            .all()
        )
        service_admin_role = Role.objects.get(name="Service Administrator", built_in=True, type="role")
        cluster_admin_role = Role.objects.get(name="Cluster Administrator", built_in=True, type="role")
        name = "Service admin policy"
        one_service_admin_policy = policy_create(
            name=name,
            role=service_admin_role,
            group=[self.group_1],
            object=[service_2],
        )
        three_services_admin_policy = policy_create(
            name=f"{name} 2",
            role=service_admin_role,
            group=[self.group_1],
            object=[service_2, service_3, service_6],
        )
        cluster_admin_policy = policy_create(
            name="Cluster admin policy",
            role=cluster_admin_role,
            group=[self.group_1],
            object=[self.cluster_1],
        )
        expected_objects_one_service = [
            {
                "id": service_2.id,
                "displayName": service_2.display_name,
                "name": service_2.name,
                "parentId": service_2.cluster_id,
                "type": "service",
            },
        ]
        expected_objects_three_services = [
            *expected_objects_one_service,
            {
                "id": service_3.id,
                "displayName": service_3.display_name,
                "name": service_3.name,
                "parentId": service_3.cluster_id,
                "type": "service",
            },
            {
                "id": service_6.id,
                "displayName": service_6.display_name,
                "name": service_6.name,
                "parentId": service_6.cluster_id,
                "type": "service",
            },
        ]
        expected_objects_cluster = [
            {
                "id": self.cluster_1.id,
                "displayName": self.cluster_1.display_name,
                "name": self.cluster_1.name,
                "parentId": None,
                "type": "cluster",
            }
        ]
        expected_queries_number = 7

        # cache django_content_type / auth_permission queries
        (self.client.v2 / "rbac" / "policies").get()

        with self.assertNumQueries(expected_queries_number):
            response = (self.client.v2 / "rbac" / "policies" / str(one_service_admin_policy.id)).get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(response.json()["objects"], expected_objects_one_service)

        with self.assertNumQueries(expected_queries_number):
            response = (self.client.v2 / "rbac" / "policies" / str(three_services_admin_policy.id)).get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(response.json()["objects"], expected_objects_three_services)

        with self.assertNumQueries(expected_queries_number):
            response = (self.client.v2 / "rbac" / "policies" / str(cluster_admin_policy.id)).get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(response.json()["objects"], expected_objects_cluster)

    def test_ordering_success(self):
        ordering_fields = {
            "name": "name",
        }

        def get_results(response, ordering_field):
            if ordering_field == "builtIn":
                return [item["isBuiltIn"] for item in response.json()["results"]]
            return [item[ordering_field] for item in response.json()["results"]]

        for model_field, ordering_field in ordering_fields.items():
            with self.subTest(ordering_field=ordering_field):
                response = (self.client.v2 / "rbac" / "policies").get(query={"ordering": ordering_field})
                self.assertListEqual(
                    get_results(response, ordering_field),
                    list(Policy.objects.order_by(model_field).values_list(model_field, flat=True)),
                )

                response = (self.client.v2 / "rbac" / "policies").get(query={"ordering": f"-{ordering_field}"})
                self.assertListEqual(
                    get_results(response, ordering_field),
                    list(Policy.objects.order_by(f"-{model_field}").values_list(model_field, flat=True)),
                )

    def test_filtering_success(self):
        self.create_user_policy.built_in = True
        self.create_user_policy.save()
        filters = {
            "id": (self.create_user_policy.pk, None, 0),
            "name": (self.create_user_policy.name, self.create_user_policy.name[1:-3].upper(), "wrong"),
        }
        partial_items_found, exact_items_found = 1, 1
        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            wrong_items_found = 1 if filter_name == "built_in" else 0
            with self.subTest(filter_name=filter_name):
                response = (self.client.v2 / "rbac" / "policies").get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], exact_items_found)

                response = (self.client.v2 / "rbac" / "policies").get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], wrong_items_found)

                if partial_value:
                    response = (self.client.v2 / "rbac" / "policies").get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], partial_items_found)
