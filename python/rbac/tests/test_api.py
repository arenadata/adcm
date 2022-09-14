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

import json

from django.test import Client
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from init_db import init
from rbac.models import Policy, Role, User
from rbac.upgrade.role import init_roles


class ApiTests(BaseTestCase):
    def setUp(self) -> None:
        self.test_user_username = "test_user"
        self.test_user_password = "test_user_password"
        self.test_user = User.objects.create_user(
            username=self.test_user_username,
            password=self.test_user_password,
            is_superuser=True,
        )
        self.client = Client(HTTP_USER_AGENT='Mozilla/5.0')
        self.login()

        init()
        init_roles()

    def test_create_policy(self):
        for request_data, response_data in policy_data:
            response: Response = self.client.post(
                path=reverse("rbac:policy-list"),
                data=request_data,
                content_type=APPLICATION_JSON,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(json.loads(response.content), response_data)

    def test_create_role(self):
        for request_data, response_data in role_data:
            response = self.client.post(
                path=reverse("rbac:role-list"),
                data=request_data,
                format="json",
                content_type=APPLICATION_JSON,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(json.loads(response.content), response_data)

    def test_patch_empty_role_id(self):
        role = Role.objects.create(
            name="Test role", module_name="rbac.roles", class_name="ModelRole"
        )
        policy = Policy.objects.create(name="Test policy", role=role, built_in=False)
        policy.user.add(self.test_user)

        path = reverse("rbac:policy-detail", kwargs={"pk": policy.pk})
        data_valid = {
            "id": policy.pk,
            "name": policy.name,
            "description": policy.description,
            "built_in": policy.built_in,
            "role": {
                "id": role.pk,
            },
        }
        response = self.client.patch(path=path, data=data_valid, content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.patch(
            path=path, data={**data_valid, **{"role": {}}}, content_type=APPLICATION_JSON
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["role"], ["This field may not be empty."])


policy_data = [
    (
        {},
        {
            "name": ["This field is required."],
            "role": ["This field is required."],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": []},
        {
            "name": ["This value does not match the required pattern."],
            "role": ["This field is required."],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": {}},
        {
            "name": ["This value does not match the required pattern."],
            "role": ["This field is required."],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": None},
        {
            "name": ["This field may not be null."],
            "role": ["This field is required."],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": None},
        {
            "role": ["This field may not be null."],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": 1},
        {
            "role": {"non_field_errors": ["Invalid data. Expected a dictionary, but got int."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": "string"},
        {
            "role": {"non_field_errors": ["Invalid data. Expected a dictionary, but got str."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": []},
        {
            "role": {"non_field_errors": ["Invalid data. Expected a dictionary, but got list."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {}},
        {
            "role": {"id": ["This field is required."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": None}},
        {
            "role": {"id": ["This field may not be null."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 1000}},
        {
            "role": {"id": ["Invalid pk \"1000\" - object does not exist."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": "string"}},
        {
            "role": {"id": ["Incorrect type. Expected pk value, received str."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 5}},
        {
            "role": ["Role with type \"business\" could not be used in policy"],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 1}},
        {
            "role": ["Role with type \"hidden\" could not be used in policy"],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": None},
        {
            "user": ["This field may not be null."],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": 1},
        {
            "user": {"non_field_errors": ["Expected a list of items but got type \"int\"."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": "string"},
        {
            "user": {"non_field_errors": ["Expected a list of items but got type \"str\"."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": {}},
        {
            "user": {"non_field_errors": ["Expected a list of items but got type \"dict\"."]},
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [1]},
        {
            "user": [{"non_field_errors": ["Invalid data. Expected a dictionary, but got int."]}],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": ["string"]},
        {
            "user": [{"non_field_errors": ["Invalid data. Expected a dictionary, but got str."]}],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{}]},
        {
            "user": [{"id": ["This field is required."]}],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": None}]},
        {
            "user": [{"id": ["This field may not be null."]}],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": "string"}]},
        {
            "user": [{"id": ["Incorrect type. Expected pk value, received str."]}],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": 1000}]},
        {
            "user": [{"id": ["Invalid pk \"1000\" - object does not exist."]}],
            "object": ["This field is required."],
        },
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": 2}], "object": None},
        {"object": ["This field may not be null."]},
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": 2}], "object": 1},
        {"object": ["the field does not match the scheme"]},
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": 2}], "object": "string"},
        {"object": ["the field does not match the scheme"]},
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": 2}], "object": {}},
        {"object": ["the field does not match the scheme"]},
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": 2}], "object": [1]},
        {"object": ["the field does not match the scheme"]},
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": 2}], "object": ["string"]},
        {"object": ["the field does not match the scheme"]},
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": 2}], "object": [{}]},
        {"object": ["the field does not match the scheme"]},
    ),
    (
        {"name": "test", "role": {"id": 90}, "user": [{"id": 2}], "object": [{"id": 1}]},
        {"object": ["the field does not match the scheme"]},
    ),
]

role_data = [
    (
        {},
        {
            "display_name": ["This field is required."],
            "child": ["This field is required."],
        },
    ),
    (
        {"display_name": [], "child": [{"id": 1}]},
        {
            "display_name": ["This value does not match the required pattern."],
        },
    ),
    (
        {"display_name": "test", "description": None, "child": [{"id": 1}]},
        {"description": ["This field may not be null."]},
    ),
    (
        {"display_name": "test", "description": [], "child": [{"id": 1}]},
        {"description": ["Not a valid string."]},
    ),
    (
        {"display_name": "test", "child": None},
        {"child": ["This field may not be null."]},
    ),
    (
        {"display_name": "test", "child": 1},
        {"child": {"non_field_errors": ["Expected a list of items but got type \"int\"."]}},
    ),
    (
        {"display_name": "test", "child": "string"},
        {"child": {"non_field_errors": ["Expected a list of items but got type \"str\"."]}},
    ),
    (
        {"display_name": "test", "child": []},
        {"child": ["Roles without children make not sense"]},
    ),
    (
        {"display_name": "test", "child": [1]},
        {"child": [{"non_field_errors": ["Invalid data. Expected a dictionary, but got int."]}]},
    ),
    (
        {"display_name": "test", "child": ["string"]},
        {"child": [{"non_field_errors": ["Invalid data. Expected a dictionary, but got str."]}]},
    ),
    (
        {"display_name": "test", "child": [{}]},
        {"child": [{"id": ["This field is required."]}]},
    ),
    (
        {"display_name": "test", "child": [{"id": "string"}]},
        {"child": [{"id": ["Incorrect type. Expected pk value, received str."]}]},
    ),
    (
        {"display_name": "test", "child": [{"id": 1000}]},
        {"child": [{"id": ["Invalid pk \"1000\" - object does not exist."]}]},
    ),
    (
        {
            "display_name": "test",
            "child": [{"id": 10000000000000000000}],
        },
        {
            "code": "OVERFLOW",
            "level": "error",
            "desc": "integer or floats in a request cause an overflow",
        },
    ),
]
