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

"""UI tests for string type config fields"""

# pylint:disable=redefined-outer-name
import os
import time

import allure
import pytest
from adcm_pytest_plugin.utils import get_data_dir

from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.locators import Common

DATADIR = get_data_dir(__file__)
BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")

NO_REQUIRED_FIELDS = [
    'no_required_string_activatable_true',
    'no_required_string_without_type',
    'no_required_string_activatable_false',
    'no_required_string_group',
]
REQUIRED_FIELDS = [
    'string_required_by_default_group',
    'string_required_by_option_group',
    'string_with_ui_options_is_false_group',
    'advanced_string_group',
    'string_required_by_default_activatable_false',
    'string_required_by_option_activatable_false',
    'string_with_ui_options_is_false_activatable_false',
    'advanced_string_activatable_false',
    'string_required_True_activatable_false',
    'string_required_by_default_without_type',
    'string_required_by_option_without_type',
    'string_with_ui_options_is_false_without_type',
    'advanced_string_without_type',
    'string_required_True_without_type',
    'string_required_by_default_activatable_true',
    'string_required_by_option_activatable_true',
    'string_with_ui_options_is_false_activatable_true',
    'string_required_True_activatable_true',
]


@pytest.fixture()
@allure.title('Upload bundle, create cluster and add service')
def service(sdk_client_fs):
    """Upload bundle, create cluster and add service"""
    bundle = sdk_client_fs.upload_from_fs(DATADIR)
    cluster = bundle.cluster_create(name='my cluster')
    cluster.service_add(name='string_fields_config_test')
    return cluster.service(name="string_fields_config_test")


@pytest.fixture()
@allure.title("Open service config page")
def ui_config(app_fs, service, login_to_adcm_over_api):  # pylint: disable=unused-argument
    """Open service config page"""
    return Configuration.from_service(app_fs, service)


@pytest.mark.parametrize("required_field", REQUIRED_FIELDS)
def test_required_string_frontend_error(ui_config, required_field):
    """Check that we have frontend error for required string if this string not filled
    Scenario:
    1. Clear required field
    2. Check that we have frontend error for required field
    3. Check that save button is not active
    """

    textboxes = ui_config.get_textboxes()
    with allure.step('Check that we have frontend error for required field and ave button is not active'):
        for textbox in textboxes:
            name = textbox.text.split(":")[0]
            if name == required_field:
                input_element = textbox.find_element(*Common.mat_input_element)
                ui_config.clear_element(input_element)
                time.sleep(2)
                error = textbox.find_element(*Common.mat_error).text
                assert f'Field [{name}] is required!' == error
                assert not ui_config.save_button_status()


@pytest.mark.parametrize("field", NO_REQUIRED_FIELDS)
def test_empty_no_required_string(field, ui_config):
    """Test UI behaviour of non-required empty field"""
    textboxes = ui_config.get_textboxes()
    with allure.step('Check that save button is active in case when no required field is empty'):
        for textbox in textboxes:
            name = textbox.text.split(":")[0]
            if name == field:
                input_element = textbox.find_element(*Common.mat_input_element)
                ui_config.clear_element(input_element)
                assert ui_config.save_button_status()
                break


@pytest.mark.parametrize("pattern", ["_group", "without_type"], ids=["groups", 'without_groups'])
def test_search_field(ui_config, pattern):
    """Insert search string and check that on page only searched fields."""

    ui_config.set_search_field(pattern)
    time.sleep(2)
    textboxes = ui_config.get_app_fields()
    with allure.step('Check that on page only searched fields'):
        visible_textboxes = [textbox.text for textbox in textboxes if textbox.is_displayed()]
        result = [textbox for textbox in visible_textboxes if textbox != '']
        assert len(result) == 5, result
        for textbox in result:
            assert pattern in textbox


def test_save_configuration(ui_config):
    """Test that we can click save configuration if no errors on page"""
    with allure.step('Check that we can click save configuration if no errors on page'):
        assert ui_config.save_button_status()
