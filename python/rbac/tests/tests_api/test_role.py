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
def test_create_role(admin_api_client):
    url = reverse("rbac:role-list")
    data = [
        (
            {},
            {
                "name": ["This field is required."],
                "parametrized_by_type": ["This field is required."],
            },
        ),
        (
            {"name": [], "parametrized_by_type": "test"},
            {"name": ["Not a valid string."], "parametrized_by_type": ["Not a valid list."]},
        ),
        (
            {"name": "test", "parametrized_by_type": ["WrongType"]},
            {"parametrized_by_type": ["Not a valid object type."]},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "description": None},
            {"description": ["This field may not be null."]},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "description": []},
            {"description": ["Not a valid string."]},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "category": 123},
            {"category": ["Not a valid list."]},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "category": ["string", 1]},
            {"category": ["Not a valid string in list."]},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "child": None},
            {"child": ["This field may not be null."]},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "child": 1},
            {"child": {"non_field_errors": ["Expected a list of items but got type \"int\"."]}},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "child": "string"},
            {"child": {"non_field_errors": ["Expected a list of items but got type \"str\"."]}},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "child": [1]},
            {
                "child": [
                    {"non_field_errors": ["Invalid data. Expected a dictionary, but got int."]}
                ]
            },
        ),
        (
            {"name": "test", "parametrized_by_type": [], "child": ["string"]},
            {
                "child": [
                    {"non_field_errors": ["Invalid data. Expected a dictionary, but got str."]}
                ]
            },
        ),
        (
            {"name": "test", "parametrized_by_type": [], "child": [{}]},
            {"child": [{"id": ["This field is required."]}]},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "child": [{"id": "string"}]},
            {"child": [{"id": ["Incorrect type. Expected pk value, received str."]}]},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "child": [{"id": 1000}]},
            {"child": [{"id": ["Invalid pk \"1000\" - object does not exist."]}]},
        ),
        (
            {"name": "test", "parametrized_by_type": [], "child": [{"id": 10000000000000000000}]},
            {
                "code": "OVERFLOW",
                "level": "error",
                "desc": "integer or floats in a request cause an overflow",
            },
        ),
    ]

    for request_data, response_data in data:
        response = admin_api_client.post(url, data=request_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert json.loads(response.content) == response_data
