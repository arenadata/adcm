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

"""API tests for request body validation"""

from typing import Tuple

import allure
import pytest
from tests.api.steps.asserts import ExpectedBody
from tests.api.testdata.generators import TestDataWithPreparedBody
from tests.api.utils.data_classes import AUTO_VALUE
from tests.api.utils.methods import Methods
from tests.api.utils.tools import NotEqual, not_set
from tests.api.utils.types import get_fields, is_fk_field, is_password_field

pytestmark = [
    pytest.mark.allure_label("API Tests", label_type="layer"),
    pytest.mark.allure_label("API base", label_type="parentSuite"),
]


def _test_patch_put_body_positive(prepare_body_data: Tuple):
    """
    Common function for positive cases of PUT and PATCH request body testing
    Includes sets of correct field values - boundary values, nullable if possible.
    """
    adcm, test_data_list = prepare_body_data
    for test_data_with_prepared_body in test_data_list:
        test_data, _ = test_data_with_prepared_body
        test_data.response.body = generate_body_for_checks(test_data_with_prepared_body)
        with allure.step(f'Assert - {test_data.description}'):
            adcm.exec_request(request=test_data.request, expected_response=test_data.response)


def generate_body_for_checks(test_data: TestDataWithPreparedBody):
    """
    Generate expected response fields values by test data
    """
    test_data, prepared_field_values = test_data
    body = ExpectedBody()
    for field in get_fields(test_data.request.endpoint.data_class):
        body.fields[field.name] = not_set
        if is_fk_field(field):
            # TODO add fk field check
            continue
        if field.default_value == AUTO_VALUE:
            continue
        if test_data.request.method == Methods.POST:
            continue
        if isinstance(body.fields[field.name], list):
            # TODO implement list checks with sorting
            continue
        if (
            test_data.request.method == Methods.PATCH
            and not field.changeable
            and field.name in prepared_field_values
            and prepared_field_values[field.name].generated_value
        ):
            body.fields[field.name] = NotEqual(test_data.request.data.get(field.name))
        elif is_password_field(field):
            body.fields[field.name] = field.f_type.placeholder
        elif expected_field_value := test_data.request.data.get(field.name):
            body.fields[field.name] = expected_field_value
    return body
