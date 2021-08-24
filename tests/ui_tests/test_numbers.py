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

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import parametrize_by_data_subdirs, get_data_dir

from tests.ui_tests.app.locators import Common
from .utils import prepare_cluster_and_get_config


pytestmark = [pytest.mark.usefixtures("login_to_adcm_over_api")]


RANGE_VALUES = [
    ("float", 0.15),
    ("float", 0),
    ("float", -1.2),
    ("integer", 4),
    ("integer", 0),
    ("integer", -3),
]


@parametrize_by_data_subdirs(__file__, 'bundles')
def test_number_validation(sdk_client_fs: ADCMClient, path, app_fs):
    """Check that we have errors and save button is not active
    for number field with values out of range
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    assert config.save_button_status()
    fields = config.get_app_fields()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    config.clear_input_element(form_field)
    assert not config.save_button_status()
    config.assert_form_field_text_equal(fields[0], "Field [numbers_test] is required!")
    config.set_element_value_in_input(form_field, "asdsa")
    config.assert_form_field_text_equal(fields[0], "Field [numbers_test] is invalid!")
    assert not config.save_button_status()
    config.set_element_value_in_input(form_field, "-111111")
    assert not config.save_button_status()
    config.assert_form_field_text_in(fields[0], "Field [numbers_test] value cannot be less than")
    config.set_element_value_in_input(form_field, "111111")
    assert not config.save_button_status()
    config.assert_form_field_text_in(fields[0], "Field [numbers_test] value cannot be greater than")


@pytest.mark.parametrize(("number_type", "value"), RANGE_VALUES)
def test_number_in_range_values(sdk_client_fs: ADCMClient, value, app_fs, number_type):
    path = get_data_dir(__file__) + "/bundles/{}-positive_and_negative".format(number_type)
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    fields = config.get_app_fields()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    config.set_element_value_in_input(form_field, str(value))
    with allure.step('Check that save button active for number fields in min-max range'):
        assert config.save_button_status()


def test_float_in_integer_field(sdk_client_fs: ADCMClient, app_fs):
    path = get_data_dir(__file__) + "/bundles/integer-positive_and_negative"
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    fields = config.get_app_fields()
    form_field = fields[0].find_elements(*Common.mat_form_field)[0]
    config.set_element_value_in_input(form_field, "1.2")
    with allure.step('Check that we cannot set float in integer field'):
        assert not config.save_button_status()
        fields = config.get_app_fields()
        config.assert_form_field_text_equal(fields[0], "Field [numbers_test] is invalid!")
