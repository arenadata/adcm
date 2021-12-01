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

import pytest
from rest_framework import status
from rest_framework.reverse import reverse


@pytest.mark.django_db
def test_create_policy(admin_api_client):
    url = reverse("rbac:policy-list")
    data = [
        (
            {},
            {
                "name": ["This field is required."],
                "role": ["This field is required."],
                "user": ["This field is required."],
            },
        ),
        (
            {"name": []},
            {
                "name": ["Not a valid string."],
                "role": ["This field is required."],
                "user": ["This field is required."],
            },
        ),
        (
            {"name": {}},
            {
                "name": ["Not a valid string."],
                "role": ["This field is required."],
                "user": ["This field is required."],
            },
        ),
        (
            {"name": None},
            {
                "name": ["This field may not be null."],
                "role": ["This field is required."],
                "user": ["This field is required."],
            },
        ),
        (
            {"name": "test", "role": None},
            {"role": ["This field may not be null."], "user": ["This field is required."]},
        ),
        (
            {"name": "test", "role": 1},
            {
                "role": {"non_field_errors": ["Invalid data. Expected a dictionary, but got int."]},
                "user": ["This field is required."],
            },
        ),
        (
            {"name": "test", "role": "string"},
            {
                "role": {"non_field_errors": ["Invalid data. Expected a dictionary, but got str."]},
                "user": ["This field is required."],
            },
        ),
        (
            {"name": "test", "role": []},
            {
                "role": {
                    "non_field_errors": ["Invalid data. Expected a dictionary, but got list."]
                },
                "user": ["This field is required."],
            },
        ),
        (
            {"name": "test", "role": {}},
            {"role": {"id": ["This field is required."]}, "user": ["This field is required."]},
        ),
        (
            {"name": "test", "role": {"id": None}},
            {"role": {"id": ["This field may not be null."]}, "user": ["This field is required."]},
        ),
        (
            {"name": "test", "role": {"id": 1000}},
            {
                "role": {"id": ["Invalid pk \"1000\" - object does not exist."]},
                "user": ["This field is required."],
            },
        ),
        (
            {"name": "test", "role": {"id": "string"}},
            {
                "role": {"id": ["Incorrect type. Expected pk value, received str."]},
                "user": ["This field is required."],
            },
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": None},
            {"user": ["This field may not be null."]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": 1},
            {"user": {"non_field_errors": ["Expected a list of items but got type \"int\"."]}},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": "string"},
            {"user": {"non_field_errors": ["Expected a list of items but got type \"str\"."]}},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": {}},
            {"user": {"non_field_errors": ["Expected a list of items but got type \"dict\"."]}},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [1]},
            {"user": [{"non_field_errors": ["Invalid data. Expected a dictionary, but got int."]}]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": ["string"]},
            {"user": [{"non_field_errors": ["Invalid data. Expected a dictionary, but got str."]}]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{}]},
            {"user": [{"id": ["This field is required."]}]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": None}]},
            {"user": [{"id": ["This field may not be null."]}]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": "string"}]},
            {"user": [{"id": ["Incorrect type. Expected pk value, received str."]}]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": 1000}]},
            {"user": [{"id": ["Invalid pk \"1000\" - object does not exist."]}]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": 3}], "object": None},
            {"object": ["This field may not be null."]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": 3}], "object": 1},
            {"object": ["the field does not match the scheme"]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": 3}], "object": "string"},
            {"object": ["the field does not match the scheme"]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": 3}], "object": {}},
            {"object": ["the field does not match the scheme"]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": 3}], "object": [1]},
            {"object": ["the field does not match the scheme"]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": 3}], "object": ["string"]},
            {"object": ["the field does not match the scheme"]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": 3}], "object": [{}]},
            {"object": ["the field does not match the scheme"]},
        ),
        (
            {"name": "test", "role": {"id": 1}, "user": [{"id": 2}], "object": [{"id": 1}]},
            {"object": ["the field does not match the scheme"]},
        ),
    ]

    admin_api_client.post(
        reverse("rbac:role-list"), data={"name": "test", "parametrized_by_type": []}, format='json'
    )
    admin_api_client.post(
        reverse("rbac:user-list"), data={"username": "test", "password": "test"}, format='json'
    )

    for request_data, response_data in data:
        response = admin_api_client.post(url, data=request_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert json.loads(response.content) == response_data
