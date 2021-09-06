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
from typing import Tuple

import allure
import pytest

from tests.api.steps.asserts import ExpectedBody
from tests.api.utils.tools import not_set
from tests.api.utils.types import get_fields

pytestmark = [
    pytest.mark.allure_label("API Tests", label_type="layer"),
    pytest.mark.allure_label("API base", label_type="parentSuite"),
    pytest.mark.xfail(reason="Group config will be refactored"),
]


def _test_patch_put_body_positive(prepare_body_data: Tuple):
    """
    Common function for positive cases of PUT and PATCH request body testing
    Includes sets of correct field values - boundary values, nullable if possible.
    """
    adcm, test_data_list = prepare_body_data
    for test_data in test_data_list:
        # Set expected response fields values
        test_data.response.body = ExpectedBody()
        for field in get_fields(test_data.request.endpoint.data_class):
            test_data.response.body.fields[field.name] = not_set
            if expected_field_value := test_data.request.data.get(field.name):
                test_data.response.body.fields[field.name] = expected_field_value
        with allure.step(f'Assert - {test_data.description}'):
            adcm.exec_request(request=test_data.request, expected_response=test_data.response)
