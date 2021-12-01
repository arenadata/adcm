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

"""UI tests for super large config"""

# pylint: disable=redefined-outer-name
import os
from typing import Set, Tuple

import allure
import pytest
from adcm_client.objects import Service
from adcm_pytest_plugin.utils import get_data_dir

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.service.page import ServiceConfigPage
from tests.ui_tests.app.configuration import Configuration

DATADIR = get_data_dir(__file__)
BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")

SERVICE_NAME = 'new_ui_config_hell'
SERVICE_DISPLAY_NAME = 'New UI Config Hell'


@pytest.fixture()
@allure.step('Upload bundle, create cluster and add service')
def ui_hell_fs(sdk_client_fs) -> Service:
    """Upload bundle, create cluster and add service"""
    bundle = sdk_client_fs.upload_from_fs(DATADIR)
    cluster = bundle.cluster_create(name='my cluster')
    return cluster.service_add(name=SERVICE_NAME)


@pytest.fixture()
@allure.title("Prepare prototype display names")
def prototype_display_names(ui_hell_fs: Service) -> Tuple[str, str]:
    """Prepare prototype display names"""
    display_header_name = ui_hell_fs.display_name
    display_names = {config['display_name'] for config in ui_hell_fs.prototype().config}
    return display_header_name, display_names


@pytest.fixture()
@allure.title('Open service configuration page')
def config_page(
    app_fs: ADCMTest, ui_hell_fs: Service, login_to_adcm_over_api  # pylint: disable=unused-argument
) -> ServiceConfigPage:
    """Get config page from service"""
    return ServiceConfigPage(app_fs.driver, app_fs.adcm.url, ui_hell_fs.cluster().id, ui_hell_fs.id).open()


@pytest.fixture()
@allure.title('Get display names from service config page')
def ui_display_names(
    app_fs: ADCMTest, ui_hell_fs, login_to_adcm_over_api  # pylint: disable=unused-argument
) -> Set[str]:
    """Get display names from service config page"""
    return Configuration.from_service(app_fs, ui_hell_fs).get_display_names()


def test_save_configuration_hell(
    config_page: ServiceConfigPage,
    prototype_display_names: Tuple[str, str],
    ui_display_names: Set[str],
):
    """
    Scenario:
    1. Get Service configuration
    2. Get display names from UI
    3. Check that config name in prototype is correct
    4. Check that in UI we have full list of display names from prototype
    5. Fill required fields and try to save
    """
    service_display_name_from_prototype, parameters_display_names = prototype_display_names
    with allure.step('Check that config name in prototype is correct'):
        assert service_display_name_from_prototype == SERVICE_DISPLAY_NAME
    with allure.step('Check that in UI we have full list of group display names from prototype'):
        group_names = filter(
            lambda name: 'group' in name
            and ('invisible' not in name or 'not invisible' in name)
            and ('advanced' not in name or 'not advanced' in name),
            parameters_display_names,
        )
        for display_name in group_names:
            assert display_name in ui_display_names, f"Group named '{display_name}' should be presented in config"
    _fill_required_fields(config_page)
    config_page.config.save_config(load_timeout=40)
    with allure.step('Ensure page is still opened'):
        config_page.wait_page_is_opened(timeout=1)
    with allure.step('Check that popup is not presented on page'):
        assert not config_page.is_popup_presented_on_page(), 'No popup should be shown after save'


@allure.step('Fill required fields')
def _fill_required_fields(config_page: ServiceConfigPage):
    simple_fill_method = config_page.config.type_in_config_field

    required_fields = {
        'integer not default required:': ('2', simple_fill_method),
        'float not default required:': ('2.2', simple_fill_method),
        'string not default required:': ('Ein neuer Tag beginnt', simple_fill_method),
        'password not default required no confirm:': ('strongestpasswordever', config_page.config.fields.fill_password),
        'text not default required:': ('This is\nthe day', simple_fill_method),
        'file not default required:': ('My only\nfriend', simple_fill_method),
        'json not default required:': ('{"Where": "the long shadow falls"}', simple_fill_method),
        'list not default required:': (['Silencer'], config_page.config.fields.add_list_values),
        'map not default required:': ({'Poccolus': 'Ragana'}, config_page.config.fields.add_map_values),
    }

    for param_display_name, value in required_fields.items():
        value_to_fill, fill_method = value
        row = config_page.config.get_config_row(param_display_name)
        config_page.scroll_to(element=row)
        fill_method(value_to_fill, row)
