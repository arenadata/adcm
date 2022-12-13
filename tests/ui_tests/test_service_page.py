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

"""UI tests for /service page"""
import os
from collections import OrderedDict
from typing import Tuple

import allure
import pytest
from _pytest.fixtures import SubRequest
from adcm_client.objects import ADCMClient, Bundle, Cluster, Host, Service
from adcm_pytest_plugin import params, utils
from tests.library.status import ADCMObjectStatusChanger
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.cluster.page import ClusterServicesPage
from tests.ui_tests.app.page.common.configuration.page import CONFIG_ITEMS
from tests.ui_tests.app.page.common.group_config_list.page import GroupConfigRowInfo
from tests.ui_tests.app.page.common.import_page.page import ImportItemInfo
from tests.ui_tests.app.page.common.status.page import (
    NEGATIVE_COLOR,
    SUCCESS_COLOR,
    StatusRowInfo,
)
from tests.ui_tests.app.page.service.page import (
    ServiceComponentPage,
    ServiceConfigPage,
    ServiceGroupConfigPage,
    ServiceImportPage,
    ServiceMainPage,
    ServiceStatusPage,
)
from tests.ui_tests.test_cluster_list_page import (
    BUNDLE_COMMUNITY,
    BUNDLE_IMPORT,
    BUNDLE_REQUIRED_FIELDS,
    CLUSTER_NAME,
    COMPONENT_NAME,
    HOST_NAME,
    PROVIDER_NAME,
    SERVICE_NAME,
)
from tests.ui_tests.utils import create_few_groups

BUNDLE_WITH_REQUIRED_COMPONENT = "cluster_required_hostcomponent"
BUNDLE_WITH_REQUIRED_IMPORT = "cluster_required_import"
BUNDLE_DEFAULT_FIELDS = "cluster_and_service_with_default_string"
BUNDLE_WITH_DESCRIPTION_FIELDS = "service_with_all_config_params"


# pylint: disable=redefined-outer-name,too-many-locals
pytestmark = pytest.mark.usefixtures("_login_to_adcm_over_api")


# !===== Fixtures =====!


@pytest.fixture()
def create_cluster_with_service(sdk_client_fs: ADCMClient) -> Tuple[Cluster, Service]:
    """Create community edition cluster and add service"""
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    return cluster, cluster.service_add(name=SERVICE_NAME)


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    """Upload cluster bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), data_dir_name))


@pytest.fixture()
@allure.title("Create community cluster with service and add host")
def create_community_cluster_with_host_and_service(
    sdk_client_fs: ADCMClient, create_host
) -> Tuple[Cluster, Service, Host]:
    """Create community cluster with service and add host"""
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    return cluster, cluster.service_add(name=SERVICE_NAME), cluster.host_add(create_host)


@pytest.fixture(params=["provider"])
@allure.title("Create host")
def create_host(request: SubRequest, sdk_client_fs: ADCMClient) -> Host:
    """Create default host using API"""
    provider_bundle = sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), request.param))
    provider = provider_bundle.provider_create(PROVIDER_NAME)
    return provider.host_create(HOST_NAME)


# !===== Tests =====!


class TestServiceMainPage:
    """Tests for the /cluster/{}/service/{}/main page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_service_main_page_by_tab(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/main page from left menu"""

        cluster, service = create_cluster_with_service
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_main_page = service_config_page.open_main_tab()
        service_main_page.check_all_elements()
        service_main_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    def test_open_admin_page_by_toolbar_in_service(self, app_fs, create_cluster_with_service):
        """Test open admin/intro page from service toolbar"""

        cluster, service = create_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_main_page.toolbar.click_admin_link()
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_open_cluster_service_page_by_toolbar(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/main page from service toolbar"""

        params = {"service_list_name": "SERVICES"}

        cluster, service = create_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_main_page.toolbar.click_link_by_name(params["service_list_name"])
        cluster_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id)
        cluster_page.wait_page_is_opened()
        cluster_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_run_action_on_service_page_by_toolbar(self, app_fs, create_cluster_with_service):
        cluster, service = create_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_main_page.toolbar.run_action(CLUSTER_NAME, "test_action")
        with allure.step("Check success job"):
            assert (
                service_main_page.header.get_in_progress_job_amount() == 1
            ), "There should be 1 in progress job in header"


class TestServiceComponentPage:
    """Tests for the /cluster/{}/service/{}/component page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_service_component_page_by_tab(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/component page from left menu"""

        cluster, service = create_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_component_page = service_main_page.open_components_tab()
        service_component_page.check_all_elements()
        service_component_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    @params.including_https
    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_run_action_from_service_component_page(self, app_fs, create_cluster_with_service):
        """Test run action from the row on /cluster/{}/service/{}/component page"""

        params = {"action_name": "switch_component_state", "expected_state": "installed"}

        cluster, service = create_cluster_with_service
        service_component_page = ServiceComponentPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        row = service_component_page.table.get_all_rows()[0]
        with service_component_page.wait_component_state_change(row):
            service_component_page.run_action_in_component_row(row, params["action_name"])
        with allure.step("Check service state has changed"):
            assert (
                service_component_page.get_component_state_from_row(row) == params["expected_state"]
            ), f"Cluster state should be {params['expected_state']}"
        with allure.step("Check success service job"):
            assert (
                service_component_page.header.get_success_job_amount() == 1
            ), "There should be 1 success service job in header"


class TestServiceConfigPage:
    """Tests for the /cluster/{}/service/{}/config page"""

    INVISIBLE_GROUPS = [
        'float_invisible',
        'boolean_invisible',
        'integer_invisible',
        'password_invisible',
        'string_invisible',
        'list_invisible',
        'file_invisible',
        'option_invisible',
        'text_invisible',
        'group_invisible',
        'structure_invisible',
        'map_invisible',
        'secrettext_invisible',
        'json_invisible',
    ]

    def test_open_service_config_page_by_tab(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/config from left menu"""

        cluster, service = create_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_config_page = service_main_page.open_config_tab()
        service_config_page.check_all_elements()
        service_config_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    def test_filter_config_on_service_config_page(self, app_fs, create_cluster_with_service):
        """Test config filtration on /cluster/{}/service/{}/config page"""

        params = {"search_param": "param1", "group_name": "core-site"}

        cluster, service = create_cluster_with_service
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        with service_config_page.config.wait_rows_change():
            service_config_page.config.search(params["search_param"])
        with allure.step(f"Check that rows are filtered by {params['search_param']}"):
            config_rows = service_config_page.config.get_all_config_rows()
            assert len(config_rows) == 2, "Rows are not filtered: there should be 1 group row and 1 sub group row"
            assert (
                service_config_page.config.get_config_row_info(config_rows[1]).name == f"{params['search_param']}:"
            ), f"Name should be {params['search_param']}"
        with service_config_page.config.wait_rows_change():
            service_config_page.config.clear_search_input()
        with allure.step("Check that rows are not filtered"):
            config_rows = service_config_page.config.get_all_config_rows()
            assert len(config_rows) == 3, "Rows are filtered: there should be 1 group row and 2 sub group rows"
        with service_config_page.config.wait_rows_change(expected_rows_amount=0):
            service_config_page.config.click_on_group(params["group_name"])

    def test_save_custom_config_on_service_config_page(self, app_fs, sdk_client_fs):
        """Test config save on /cluster/{}/service/{}/config page"""

        params = {
            "config_name_new": "test_name",
            "config_name_old": "init",
            "config_parameters_amount": 28,
        }
        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_DESCRIPTION_FIELDS)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_config_page.config.fill_config_fields_with_test_values()
        service_config_page.config.set_description(params["config_name_new"])
        service_config_page.config.save_config()
        service_config_page.config.compare_versions(params["config_name_old"])
        service_config_page.config.check_config_fields_history_with_test_values()
        with allure.step("Check invisible params"):
            config = service.config()
            assert (
                len(config.keys()) == params["config_parameters_amount"]
            ), f"There are should be {params['config_parameters_amount']} config parameters"
            for group in self.INVISIBLE_GROUPS:
                assert group in config.keys(), "Invisible group should be present in config object"

    def test_save_advanced_config_on_service_config_page(self, app_fs, sdk_client_fs):
        """Test config save with advanced params on /cluster/{}/service/{}/config page"""

        params = {
            "config_name_new": "test_name",
            "config_name_old": "init",
            "rows_amount": 16,
        }
        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, "service_with_advanced_params")
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        with allure.step("Check that rows are invisible"):
            config_rows = service_config_page.config.get_all_config_rows()
            assert len(config_rows) == 0, "Rows should be hidden"
        service_config_page.config.click_on_advanced()
        with allure.step("Check that rows are visible"):
            config_rows = service_config_page.config.get_all_config_rows()
            assert len(config_rows) == params["rows_amount"], f"There should be {params['rows_amount']} rows"
        service_config_page.config.fill_config_fields_with_test_values()
        service_config_page.config.set_description(params["config_name_new"])
        service_config_page.config.save_config()
        service_config_page.config.compare_versions(params["config_name_old"])
        service_config_page.config.check_config_fields_history_with_test_values()

    @pytest.mark.skip("https://tracker.yandex.ru/ADCM-3017")
    @pytest.mark.parametrize(
        "bundle_name",
        ["password_no_confirm_false_required_false", "password_no_confirm_true_required_false"],
    )
    def test_password_required_false_in_config_on_service_config_page(self, app_fs, sdk_client_fs, bundle_name):
        """Test password field on /cluster/{}/service/{}/config page"""

        with allure.step("Create cluster and service with not required password in config"):
            bundle = cluster_bundle(sdk_client_fs, bundle_name)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        with allure.step("Check save button is enabled"):
            assert not service_config_page.config.is_save_btn_disabled(), "Save button should be enabled"
        service_config_page.config.save_config()
        with allure.step("Check params"):
            assert service.config() == OrderedDict([('password', None)]), "There should be empty password value"

    def test_password_no_confirm_false_required_true_in_config_on_service_config_page(self, app_fs, sdk_client_fs):
        """Test password field on /cluster/{}/service/{}/config page"""

        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, "password_no_confirm_false_required_true")
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        with allure.step("Check save button is disabled"):
            assert service_config_page.config.is_save_btn_disabled(), "Save button should be disabled"
            service_config_page.config.check_field_is_required("password")
            service_config_page.config.check_password_confirm_required("password")
        password_row = service_config_page.config.get_all_config_rows()[0]
        with allure.step("Check confirm is required"):
            service_config_page.config.type_in_field_with_few_inputs(password_row, values=["test"])
            service_config_page.config.check_password_confirm_required("password")
        with allure.step("Check filled password and confirm enable to save"):
            service_config_page.config.type_in_field_with_few_inputs(password_row, values=["test", "test"], clear=True)
            service_config_page.config.save_config()
        with allure.step("Check params"):
            assert service.config()["password"] is not None, "There should be password value"

    def test_password_no_confirm_true_required_true_in_config_on_service_config_page(self, app_fs, sdk_client_fs):
        """Test password field on /cluster/{}/service/{}/config page"""

        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, "password_no_confirm_true_required_true")
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        password_row = service_config_page.config.get_all_config_rows()[0]
        with allure.step("Check save button is disabled"):
            assert service_config_page.config.is_save_btn_disabled(), "Save button should be disabled"
            service_config_page.config.check_field_is_required("password")
            assert (
                service_config_page.config.get_amount_of_inputs_in_row(password_row) == 1
            ), "In password row should be only 1 field"
        with allure.step("Check filled password and confirm enable to save"):
            service_config_page.config.type_in_field_with_few_inputs(password_row, values=["test"], clear=True)
            service_config_page.config.save_config()
        with allure.step("Check params"):
            assert service.config()["password"] is not None, "There should be password value"

    def test_reset_config_in_row_on_service_config_page(self, app_fs, create_cluster_with_service):
        """Test config reset on /cluster/{}/service/{}/config page"""

        params = {
            "row_name": "param1",
            "row_value_new": "test",
            "row_value_old": "",
            "config_name": "test_name",
        }

        cluster, service = create_cluster_with_service
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        config_row = service_config_page.config.get_all_config_rows()[0]
        service_config_page.config.type_in_field_with_few_inputs(
            row=config_row, values=[params["row_value_new"]], clear=True
        )
        service_config_page.config.set_description(params["config_name"])
        service_config_page.config.save_config()

        config_row = service_config_page.config.get_all_config_rows()[0]
        service_config_page.config.reset_to_default(row=config_row)
        service_config_page.config.assert_input_value_is(
            expected_value=params["row_value_old"], display_name=params["row_name"]
        )
        with allure.step("Check invisible params"):
            config = service.config()
            assert len(config.keys()) == 15, "There are should be 15 config parameters"
            for group in self.INVISIBLE_GROUPS:
                assert group in config.keys(), "Invisible group should be present in config object"

    def test_field_validation_on_service_config_page(self, app_fs, sdk_client_fs):
        """Test config fields validation on /cluster/{}/service/{}/config page"""

        params = {
            'pass_name': 'Important password',
            'req_name': 'Required item',
            'not_req_name': 'Just item',
            'wrong_value': 'test',
        }

        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_REQUIRED_FIELDS)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_config_page.config.check_password_confirm_required(params['pass_name'])
        service_config_page.config.check_field_is_required(params['req_name'])
        config_row = service_config_page.config.get_all_config_rows()[0]
        service_config_page.config.type_in_field_with_few_inputs(row=config_row, values=[params['wrong_value']])
        service_config_page.config.check_field_is_invalid_error(params['not_req_name'])
        service_config_page.config.check_config_warn_icon_on_left_menu()
        with allure.step("Check save button is disabled"):
            assert service_config_page.config.is_save_btn_disabled(), "Save button should be disabled"

        service_config_page.toolbar.check_warn_button(
            tab_name="test_service",
            expected_warn_text=[
                'Test cluster has an issue with its config',
                'test_service has an issue with its config',
            ],
        )

    def test_field_validation_on_service_config_page_with_default_value(self, app_fs, sdk_client_fs):
        """Test config fields validation on /cluster/{}/service/{}/config page"""

        params = {'field_name': 'string', 'new_value': 'test', "config_name": "test_name"}

        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_DEFAULT_FIELDS)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_config_page.config.clear_field_by_keys(params['field_name'])
        service_config_page.config.check_field_is_required(params['field_name'])
        with allure.step("Check save button is disabled"):
            assert service_config_page.config.is_save_btn_disabled(), "Save button should be disabled"
        service_config_page.config.type_in_field_with_few_inputs(
            row=service_config_page.config.get_all_config_rows()[0], values=[params['new_value']]
        )
        service_config_page.config.save_config()
        service_config_page.config.assert_input_value_is(
            expected_value=params["new_value"], display_name=params["field_name"]
        )

    def test_field_tooltips_on_service_config_page(self, app_fs, sdk_client_fs):
        """Test config fields tooltips on /cluster/{}/service/{}/config page"""

        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_DESCRIPTION_FIELDS)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        for item in CONFIG_ITEMS:
            service_config_page.config.check_text_in_tooltip(item, f"Test description {item}")

    @pytest.mark.full()
    def test_save_configuration_hell_on_service_config_page(self, app_fs, sdk_client_fs):
        """
        UI test for super large config
        Scenario:
        1. Get Service configuration
        2. Get display names from UI
        3. Check that config name in prototype is correct
        4. Check that in UI we have full list of display names from prototype
        5. Fill required fields and try to save
        """

        required_fields = {
            'integer not default required:': (['2']),
            'float not default required:': (['2.2']),
            'string not default required:': (['Ein neuer Tag beginnt']),
            'password not default required no confirm:': (['strongestpasswordever']),
            'text not default required:': (['This is\nthe day']),
            'file not default required:': (['My only\nfriend']),
            'json not default required:': (['{"Where": "the long shadow falls"}']),
            'list not default required:': (['Silencer']),
            'map not default required:': (['Poccolus', 'Ragana', 'Poccolus', 'Ragana']),
        }
        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, "config_hell_service")
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name='service_ui_config_hell')
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        with allure.step('Check that config name in prototype is correct'):
            assert service.display_name == 'New UI Config Hell'
        with allure.step('Check that in UI we have full list of group display names from prototype'):
            parameters_display_names = {config['display_name'] for config in service.prototype().config}
            group_names = filter(
                lambda name: 'group' in name
                and ('invisible' not in name or 'not invisible' in name)
                and ('advanced' not in name or 'not advanced' in name),
                parameters_display_names,
            )
            ui_display_names = service_config_page.config.get_all_config_rows_names()
            config_group_names = [n.text for n in service_config_page.config.get_group_names()]
            for display_name in group_names:
                assert (
                    display_name in ui_display_names or display_name in config_group_names
                ), f"Config named '{display_name}' should be presented in config"
        with allure.step('Fill required fields'):
            for param_display_name, value in required_fields.items():
                row = service_config_page.config.get_config_row(param_display_name)
                service_config_page.config.type_in_field_with_few_inputs(row=row, values=value)
        service_config_page.config.save_config(load_timeout=40)
        with allure.step('Ensure page is still opened'):
            service_config_page.wait_page_is_opened(timeout=15)
        with allure.step('Check that popup is not presented on page'):
            assert not service_config_page.is_popup_presented_on_page(), 'No popup should be shown after save'


class TestServiceGroupConfigPage:
    """Tests for the /cluster/{}/service/{}/group_config page"""

    def test_open_by_tab_group_config_service_page(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/group_config from left menu"""

        cluster, service = create_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        group_conf_page = service_main_page.open_group_config_tab()
        group_conf_page.check_all_elements()
        group_conf_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    def test_create_group_config_service(self, app_fs, create_cluster_with_service):
        """Test create group config on /cluster/{}/service/{}/group_config"""

        params = {
            'name': 'Test name',
            'description': 'Test description',
        }

        cluster, service = create_cluster_with_service

        service_group_conf_page = ServiceGroupConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        with service_group_conf_page.group_config.wait_rows_change(expected_rows_amount=1):
            service_group_conf_page.group_config.create_group(name=params['name'], description=params['description'])
        group_row = service_group_conf_page.group_config.get_all_config_rows()[0]
        with allure.step("Check created row in service"):
            group_info = service_group_conf_page.group_config.get_config_row_info(group_row)
            assert group_info == GroupConfigRowInfo(
                name=params['name'], description=params['description']
            ), "Row value differs in service groups"
        with service_group_conf_page.group_config.wait_rows_change(expected_rows_amount=0):
            service_group_conf_page.group_config.delete_row(group_row)

    def test_check_pagination_on_group_config_service_page(self, app_fs, create_cluster_with_service):
        """Test pagination on /cluster/{}/service/{}/group_config page"""

        cluster, service = create_cluster_with_service
        group_conf_page = ServiceGroupConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        create_few_groups(group_conf_page.group_config)
        group_conf_page.table.check_pagination(second_page_item_amount=1)


class TestServiceStatusPage:
    """Tests for the /cluster/{}/service/{}/status page"""

    def test_open_by_tab_service_status_page(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/status from left menu"""

        cluster, service = create_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_status_page = service_main_page.open_status_tab()
        service_status_page.check_all_elements()
        service_status_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    def test_status_on_service_status_page(
        self, app_fs, adcm_fs, sdk_client_fs, create_community_cluster_with_host_and_service
    ):
        """Changes status on /cluster/{}/service/{}/status page"""

        successful = 'successful 1/1'
        negative = 'successful 0/1'
        success_status = [
            StatusRowInfo(True, 'test_service', successful, SUCCESS_COLOR, None),
            StatusRowInfo(True, 'first', successful, SUCCESS_COLOR, None),
            StatusRowInfo(True, None, None, None, 'test-host'),
        ]
        component_negative_status = [
            StatusRowInfo(False, 'test_service', negative, NEGATIVE_COLOR, None),
            StatusRowInfo(False, 'first', negative, NEGATIVE_COLOR, None),
            StatusRowInfo(False, None, None, None, 'test-host'),
        ]
        cluster, service, host = create_community_cluster_with_host_and_service
        cluster_component = cluster.service(name=SERVICE_NAME).component(name=COMPONENT_NAME)
        cluster.hostcomponent_set((host, cluster_component))

        service_status_page = ServiceStatusPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        status_changer = ADCMObjectStatusChanger(sdk_client_fs, adcm_fs)
        with allure.step("Check positive status"):
            status_changer.enable_cluster(cluster)
            service_status_page.driver.refresh()
            service_status_page.compare_current_and_expected_state(success_status)
        with allure.step("Check negative status on service"):
            status_changer.set_component_negative_status((host, cluster_component))
            service_status_page.driver.refresh()
            service_status_page.compare_current_and_expected_state(component_negative_status)
        with allure.step("Check collapse button"):
            with service_status_page.wait_rows_collapsed():
                service_status_page.click_collapse_all_btn()
            assert len(service_status_page.get_all_rows()) == 1, "Status rows should have been collapsed"


class TestServiceImportPage:
    """Tests for the /cluster/{}/service/{}/import page"""

    def test_open_by_tab_service_import_page(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/import from left menu"""

        cluster, service = create_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_import_page = service_main_page.open_import_tab()
        service_import_page.check_all_elements()
        service_import_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    def test_import_from_service_import_page(self, app_fs: ADCMTest, sdk_client_fs: ADCMClient):
        """Test service import on /cluster/{}/service/{}/import page"""

        params = {
            "message": "Successfully saved",
            "import_cluster_name": "Import cluster",
            "import_service_name": "Pre-uploaded Dummy service to import",
        }
        with allure.step("Create main cluster"):
            cluster = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY).cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        with allure.step("Create cluster to import"):
            cluster_import = cluster_bundle(sdk_client_fs, BUNDLE_IMPORT).cluster_create(
                name=params["import_cluster_name"]
            )
            cluster_import.service_add(name=params["import_service_name"])
        service_import_page = ServiceImportPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        import_item = service_import_page.get_import_items()[0]
        with allure.step("Check import on import page"):
            assert service_import_page.get_import_item_info(import_item) == ImportItemInfo(
                'Pre-uploaded Dummy service to import', 'Pre-uploaded Dummy service to import 2.5'
            ), "Text in import item changed"
        service_import_page.close_info_popup()
        service_import_page.click_checkbox_in_import_item(import_item)
        service_import_page.click_save_btn()
        with allure.step("Check that import is saved"):
            assert service_import_page.get_info_popup_text() == params["message"], "No message about success"
            assert service_import_page.is_chxb_in_item_checked(
                import_item
            ), "Checkbox with import should have been checked"

    def test_warning_on_service_import_page(self, app_fs, sdk_client_fs):
        """Test import warning !"""

        with allure.step("Create cluster"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_REQUIRED_IMPORT)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_import_page = ServiceImportPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_import_page.config.check_import_warn_icon_on_left_menu()
        service_import_page.toolbar.check_warn_button(
            tab_name="test cluster",
            expected_warn_text=[
                'Test cluster has an issue with required import',
                'test_service has an issue with required import',
            ],
        )
