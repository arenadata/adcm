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

import os
import time

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir

from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.locators import Common, ConfigurationLocators

# pylint: disable=redefined-outer-name

DATADIR = get_data_dir(__file__)
BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")


ACTIVATABLE_GROUPS = [("activatable_active_group", True), ("activatable_group", False)]
INVISIBLE_GROUPS = [
    "invisible_advanced_activatable_active_group",
    "invisible_activatable_active_group",
    "advanced_invisible_inactive_activatable_group",
    "invisible_inactive_activatable_group",
    "invisible_group",
    "advanced_invisible_group",
]


@pytest.fixture()
@allure.step('Upload bundle, create cluster and add service')
def service(sdk_client_fs):
    bundle = sdk_client_fs.upload_from_fs(DATADIR)
    cluster = bundle.cluster_create(name='group_ui_options_test')
    cluster.service_add(name='group_ui_options_test')
    return cluster.service(name="group_ui_options_test")


@pytest.fixture()
@allure.title('Open Configuration page')
def ui_config(app_fs, service, login_to_adcm_over_api):  # pylint: disable=unused-argument
    return Configuration.from_service(app_fs, service)


@pytest.fixture(params=[(False, 3), (True, 6)], ids=['advanced_disabled', 'advanced'])
def group_elements(ui_config, request):
    enable_advanced, expected_elements = request.param
    if enable_advanced:
        ui_config.show_advanced()
        assert ui_config.advanced
    return ui_config.get_group_elements(), expected_elements


@pytest.fixture()
def activatable_with_not_filled_required_fields(ui_config):
    config_groups = ui_config.driver.find_elements(*Common.mat_expansion_panel)
    group_for_edition = ""
    for group in config_groups:
        if group.text.split("\n")[0] == "activatable_active_group":
            group_for_edition = group
            break
    config_fields = group_for_edition.find_elements(*ConfigurationLocators.app_fields_text_boxes)
    for config in config_fields[0:2]:
        input_element = config.find_element(*Common.mat_input_element)
        ui_config.clear_element(input_element)
    toogle = group_for_edition.find_element(*Common.mat_slide_toggle)
    if 'mat-checked' in toogle.get_attribute("class"):
        toogle.click()
    return ui_config.save_button_status()


def test_group_elements_count(group_elements):
    elements, expected_elements = group_elements
    with allure.step('Check group elements count'):
        assert len(elements) == expected_elements, "Group elements count doesn't equal expected"


@pytest.mark.usefixtures("group_elements")
def test_save_groups(ui_config, sdk_client_fs: ADCMClient):
    app_fields = ui_config.get_app_fields()
    for textbox in app_fields:
        if "field_for_group_without_options:" in textbox.text:
            input_element = textbox.find_element(*Common.mat_input_element)
            ui_config.clear_element(input_element)
            time.sleep(2)
            input_element.send_keys("new value")
            break
    ui_config.save_configuration()
    service = sdk_client_fs.cluster(name="group_ui_options_test").service(name="group_ui_options_test")
    config = service.config()
    with allure.step('Check that configuration was saved'):
        assert (
            config['group_ui_options_disabled']['field_for_group_without_options'] == 'new value'
        ), "New configuration value wasn't applied"
        assert len(config.keys()) == 12
        for group in INVISIBLE_GROUPS:
            assert group in config.keys(), "Invisible group should be present in config object"


@pytest.mark.parametrize(("config_name", "activatable"), ACTIVATABLE_GROUPS, ids=["Active True", "Active False"])
def test_activatable_group_status(config_name, activatable, ui_config):
    """Check activatable group status after config creation
    Scenario:
    1. Find group by name
    2. Check group status with config
    """
    group_elements = ui_config.get_group_elements()
    toogle_status = 'No toogle status'
    status_text = ''
    with allure.step('Check group status with config'):
        for group in group_elements:
            if group.text == config_name:
                toogle = group.find_element(*Common.mat_slide_toggle)
                status_text = toogle.get_attribute("class")
                toogle_status = 'mat-checked' in status_text
                break
        assert toogle_status == activatable, status_text


def test_activatable_with_not_filled_required_fields(activatable_with_not_filled_required_fields):
    with allure.step('Check that can save config if we have ' 'disabed activatable group with empty required fields'):
        assert activatable_with_not_filled_required_fields
