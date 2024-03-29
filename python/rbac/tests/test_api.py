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


from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from rbac.models import Policy, Role


class ApiTests(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        int_1000 = 1000

        cluster_adm_role_pk = Role.objects.get(name="Cluster Administrator").pk
        self.policy_data = [
            (
                {},
                "name - This field is required.;object - This field is required.;role - This field is required.;"
                "group - This field is required.;",
            ),
            (
                {"name": []},
                (
                    "name - This value does not match the required pattern.;"
                    "object - This field is required.;role - This field is required.;group - This field is required.;"
                ),
            ),
            (
                {"name": {}},
                (
                    "name - This value does not match the required pattern.;"
                    "object - This field is required.;role - This field is required.;group - This field is required.;"
                ),
            ),
            (
                {"name": None},
                (
                    "name - This field may not be null.;object - This field is required.;"
                    "role - This field is required.;group - This field is required.;"
                ),
            ),
            (
                {"name": "test", "role": None},
                "object - This field is required.;role - This field may not be null.;"
                "group - This field is required.;",
            ),
            (
                {"name": "test", "role": 1},
                (
                    "object - This field is required.;non_field_errors - Invalid data. "
                    "Expected a dictionary, but got int.;group - This field is required.;"
                ),
            ),
            (
                {"name": "test", "role": "string"},
                (
                    "object - This field is required.;non_field_errors - Invalid data. "
                    "Expected a dictionary, but got str.;group - This field is required.;"
                ),
            ),
            (
                {"name": "test", "role": []},
                (
                    "object - This field is required.;non_field_errors - Invalid data. "
                    "Expected a dictionary, but got list.;group - This field is required.;"
                ),
            ),
            (
                {"name": "test", "role": {}},
                "object - This field is required.;id - This field is required.;group - This field is required.;",
            ),
            (
                {"name": "test", "role": {"id": None}},
                "object - This field is required.;id - This field may not be null.;group - This field is required.;",
            ),
            (
                {"name": "test", "role": {"id": int_1000}},
                f'object - This field is required.;id - Invalid pk "{int_1000}" - object does not exist.;'
                f"group - This field is required.;",
            ),
            (
                {"name": "test", "role": {"id": "string"}},
                "object - This field is required.;id - Incorrect type. Expected pk value, received str.;"
                "group - This field is required.;",
            ),
            (
                {"name": "test", "role": {"id": Role.objects.get(name="Create provider").pk}},
                'object - This field is required.;role - Role with type "business" could not be used in policy;'
                "group - This field is required.;",
            ),
            (
                {"name": "test", "role": {"id": Role.objects.get(name="Add host").pk}},
                'object - This field is required.;role - Role with type "hidden" could not be used in policy;'
                "group - This field is required.;",
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": None},
                "object - This field is required.;group - This field may not be null.;",
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": 1},
                'object - This field is required.;non_field_errors - Expected a list of items but got type "int".;',
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": "string"},
                'object - This field is required.;non_field_errors - Expected a list of items but got type "str".;',
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": {}},
                'object - This field is required.;non_field_errors - Expected a list of items but got type "dict".;',
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": [1]},
                (
                    "object - This field is required.;non_field_errors - Invalid data. "
                    "Expected a dictionary, but got int.;"
                ),
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": ["string"]},
                (
                    "object - This field is required.;non_field_errors - Invalid data. "
                    "Expected a dictionary, but got str.;"
                ),
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": [{}]},
                "object - This field is required.;id - This field is required.;",
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": [{"id": None}]},
                "object - This field is required.;id - This field may not be null.;",
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": [{"id": "string"}]},
                "object - This field is required.;id - Incorrect type. Expected pk value, received str.;",
            ),
            (
                {"name": "test", "role": {"id": cluster_adm_role_pk}, "group": [{"id": int_1000}]},
                f'object - This field is required.;id - Invalid pk "{int_1000}" - object does not exist.;',
            ),
            (
                {
                    "name": "test",
                    "role": {"id": cluster_adm_role_pk},
                    "group": [{"id": self.test_user_group.pk}],
                    "object": None,
                },
                "object - This field may not be null.;",
            ),
            (
                {
                    "name": "test",
                    "role": {"id": cluster_adm_role_pk},
                    "group": [{"id": self.test_user_group.pk}],
                    "object": 1,
                },
                "object - the field does not match the scheme;",
            ),
            (
                {
                    "name": "test",
                    "role": {"id": cluster_adm_role_pk},
                    "group": [{"id": self.test_user_group.pk}],
                    "object": "string",
                },
                "object - the field does not match the scheme;",
            ),
            (
                {
                    "name": "test",
                    "role": {"id": cluster_adm_role_pk},
                    "group": [{"id": self.test_user_group.pk}],
                    "object": {},
                },
                "object - the field does not match the scheme;",
            ),
            (
                {
                    "name": "test",
                    "role": {"id": cluster_adm_role_pk},
                    "group": [{"id": self.test_user_group.pk}],
                    "object": [1],
                },
                "object - the field does not match the scheme;",
            ),
            (
                {
                    "name": "test",
                    "role": {"id": cluster_adm_role_pk},
                    "group": [{"id": self.test_user_group.pk}],
                    "object": ["string"],
                },
                "object - the field does not match the scheme;",
            ),
            (
                {
                    "name": "test",
                    "role": {"id": cluster_adm_role_pk},
                    "group": [{"id": self.test_user_group.pk}],
                    "object": [{}],
                },
                "object - the field does not match the scheme;",
            ),
            (
                {
                    "name": "test",
                    "role": {"id": cluster_adm_role_pk},
                    "group": [{"id": self.test_user_group.pk}],
                    "object": [{"id": 1}],
                },
                "object - the field does not match the scheme;",
            ),
        ]

        add_host_role_pk = Role.objects.get(name="Add host").pk
        self.role_data = [
            (
                {},
                "display_name - This field is required.;child - This field is required.;",
            ),
            (
                {"display_name": [], "child": [{"id": add_host_role_pk}]},
                "display_name - This value does not match the required pattern.;",
            ),
            (
                {"display_name": "test", "description": None, "child": [{"id": add_host_role_pk}]},
                "description - This field may not be null.;",
            ),
            (
                {"display_name": "test", "description": [], "child": [{"id": add_host_role_pk}]},
                "description - Not a valid string.;",
            ),
            (
                {"display_name": "test", "child": None},
                "child - This field may not be null.;",
            ),
            (
                {"display_name": "test", "child": add_host_role_pk},
                'non_field_errors - Expected a list of items but got type "int".;',
            ),
            (
                {"display_name": "test", "child": "string"},
                'non_field_errors - Expected a list of items but got type "str".;',
            ),
            (
                {"display_name": "test", "child": []},
                "child - Roles without children make not sense;",
            ),
            (
                {"display_name": "test", "child": [add_host_role_pk]},
                "non_field_errors - Invalid data. Expected a dictionary, but got int.;",
            ),
            (
                {"display_name": "test", "child": ["string"]},
                "non_field_errors - Invalid data. Expected a dictionary, but got str.;",
            ),
            (
                {"display_name": "test", "child": [{}]},
                "id - This field is required.;",
            ),
            (
                {"display_name": "test", "child": [{"id": "string"}]},
                "id - Incorrect type. Expected pk value, received str.;",
            ),
            (
                {"display_name": "test", "child": [{"id": int_1000}]},
                f'id - Invalid pk "{int_1000}" - object does not exist.;',
            ),
        ]

    def test_create_policy(self):
        for request_data, response_data in self.policy_data:
            response: Response = self.client.post(
                path=reverse(viewname="v1:rbac:policy-list"),
                data=request_data,
                content_type=APPLICATION_JSON,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response_data, response.json()["desc"])

    def test_create_role(self):
        for request_data, response_data in self.role_data:
            response = self.client.post(
                path=reverse(viewname="v1:rbac:role-list"),
                data=request_data,
                format="json",
                content_type=APPLICATION_JSON,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()["desc"], response_data)

    def test_patch_empty_role_id(self):
        role = Role.objects.create(name="Test role", module_name="rbac.roles", class_name="ModelRole")
        policy = Policy.objects.create(name="Test policy", role=role, built_in=False)
        policy.group.add(self.test_user_group)

        path = reverse(viewname="v1:rbac:policy-detail", kwargs={"pk": policy.pk})
        data_valid = {
            "id": policy.pk,
            "name": policy.name,
            "description": policy.description,
            "built_in": policy.built_in,
            "role": {
                "id": role.pk,
            },
            "group": [{"id": self.test_user_group.pk}],
        }
        response = self.client.patch(path=path, data=data_valid, content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.patch(path=path, data={**data_valid, **{"role": {}}}, content_type=APPLICATION_JSON)  # noqa: PIE800

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["desc"], "role - This field may not be empty.;")
