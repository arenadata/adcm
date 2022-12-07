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

"""Test designed to check config save with different config params"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Service
from adcm_pytest_plugin.utils import get_data_dir
from tests.ui_tests.app.page.cluster.page import ClusterGroupConfigConfig
from tests.ui_tests.app.page.service.page import ServiceConfigPage

CONFIG_DIR = "config_save"
CLUSTER_NAME = "Test cluster"


@pytest.fixture(name="create_cluster")
def cluster_config_save(sdk_client_fs: ADCMClient) -> Cluster:
    """Upload cluster bundle and create cluster"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, CONFIG_DIR))
    return bundle.cluster_create(name=CLUSTER_NAME)


@pytest.mark.full()
@pytest.mark.usefixtures("_login_to_adcm_over_api")
class TestServiceConfigSave:
    """Tests to check cluster config save"""

    INVISIBLE_GROUPS = [
        "string",
        "structure",
    ]

    STRUCTURE_ROW_NAME = "structure"
    STRING_ROW_NAME = "string"
    CONFIG_NAME_NEW = "test_name"
    CONFIG_NAME_OLD = "init"
    GROUP_NAME = "service-group"
    CONFIG_PARAM_AMOUNT = 2
    CONFIG_ADVANCED_PARAM_AMOUNT = 1
    CHANGE_STRUCTURE_CODE = 12
    CHANGE_STRUCTURE_COUNTRY = "test-country"
    STRUCTURE_MAP = {"test-country": "12", "test-country-0": "12", "test-country-1": "13", "test-country-2": "14"}
    STRUCTURE_LIST = {'12': 'test-country', 'test-country-0': '12', 'test-country-1': '13', 'test-country-2': '14'}

    @allure.step("Save config and check popup")
    def _save_config_and_refresh(self, config):
        config.config.save_config()
        assert not config.is_popup_presented_on_page(), "No popup should be shown after save"
        config.driver.refresh()

    @staticmethod
    def _check_read_only_params(config_page):
        """Method to check read only state of params"""
        string_row, structure_row, *_ = config_page.config.get_all_config_rows()
        assert not config_page.config.is_element_read_only(string_row), "Config param must be writable"
        assert config_page.config.is_element_read_only(structure_row), "Config param must be read_only"

    def check_invisible_params(self, service: Service, parameters_amount: int) -> None:
        """Method to check invisible groups in config"""
        config = service.config()
        assert len(config) == parameters_amount, f"Amount of config parameters should be {parameters_amount}"
        for group in self.INVISIBLE_GROUPS:
            assert group in config, "Invisible group should be present in config object"

    def check_advanced_params(self, config_page):
        """Method to check advanced params in config"""
        assert (
            config_page.config.rows_amount == self.CONFIG_ADVANCED_PARAM_AMOUNT
        ), "Advanced params should be present only when 'Advanced' is enabled"
        config_page.config.click_on_advanced()
        assert (
            config_page.config.rows_amount == self.CONFIG_PARAM_AMOUNT
        ), "All params should be present when 'Advanced' is enabled"
        config_page.config.click_on_advanced()

    def test_config_save(self, app_fs, sdk_client_fs, create_cluster):
        """Test to check config save with default params"""
        with allure.step("Create cluster and service"):
            cluster = create_cluster
            service = cluster.service_add(name="service_config_default")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.config.set_description(self.CONFIG_NAME_NEW)
            self._save_config_and_refresh(service_config_page)
            service_config_page.config.compare_versions(self.CONFIG_NAME_OLD)

        with allure.step("Create service group config"):
            service_group_config = service.group_config_create(self.GROUP_NAME)
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.config.set_description(self.CONFIG_NAME_NEW)

    def test_config_empty(self, app_fs, sdk_client_fs, create_cluster):
        """Test to check config save with empty params"""
        with allure.step("Create cluster and service"):
            cluster = create_cluster
            service = cluster.service_add(name="service_config_empty")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.config.set_description(self.CONFIG_NAME_NEW)
            self._save_config_and_refresh(service_config_page)
            service_config_page.config.is_history_disabled()

        with allure.step("Add params to empty config and save"):
            service_config_page.config.click_add_item_btn_in_row(self.STRUCTURE_ROW_NAME)
            service_config_page.config.type_in_field_with_few_inputs(
                self.STRUCTURE_ROW_NAME, [self.CHANGE_STRUCTURE_COUNTRY, self.CHANGE_STRUCTURE_CODE], clear=False
            )
            service_config_page.config.save_config()

        with allure.step("Create group config and check params from config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.config.assert_map_value_is(
                expected_value={self.CHANGE_STRUCTURE_COUNTRY: str(self.CHANGE_STRUCTURE_CODE)},
                display_name=self.STRUCTURE_ROW_NAME,
            )

        with allure.step("Add new params in service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            structure_params = [self.CHANGE_STRUCTURE_COUNTRY, self.CHANGE_STRUCTURE_CODE]
            for i in range(3):
                service_config_page.config.click_add_item_btn_in_row(self.STRUCTURE_ROW_NAME)
                structure_params.extend((f"{self.CHANGE_STRUCTURE_COUNTRY}-{i}", self.CHANGE_STRUCTURE_CODE + i))
                service_config_page.config.type_in_field_with_few_inputs(
                    self.STRUCTURE_ROW_NAME, structure_params, clear=True
                )
            self._save_config_and_refresh(service_config_page)

        with allure.step("Check config params after save"):
            service_config_page.config.assert_map_value_is(
                expected_value=self.STRUCTURE_MAP, display_name=self.STRUCTURE_ROW_NAME
            )

        with allure.step("Check group config params from config after save"):
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.config.assert_map_value_is(
                expected_value=self.STRUCTURE_MAP, display_name=self.STRUCTURE_ROW_NAME
            )

    def test_config_save_required(self, app_fs, sdk_client_fs, create_cluster):
        """Test to check config can not be saved when required params is empty"""
        with allure.step("Create cluster and service"):
            cluster = create_cluster
            service = cluster.service_add(name="service_config_required")

        with allure.step("Create service config and check save button"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            assert service_config_page.config.is_save_btn_disabled(), "Save button must be disabled"

    def test_config_save_invisible(self, app_fs, sdk_client_fs, create_cluster):
        """Test to check config save with ui option invisible"""
        with allure.step("Create cluster and service"):
            cluster = create_cluster
            service = cluster.service_add(name="service_invisible")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()

        with allure.step("Check config ui option invisible"):
            self.check_invisible_params(service, self.CONFIG_PARAM_AMOUNT)
            self._save_config_and_refresh(service_config_page)
            self.check_invisible_params(service, self.CONFIG_PARAM_AMOUNT)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.config.set_description(self.CONFIG_NAME_NEW)

        with allure.step("Save group config and check that popup is not presented on page"):
            cluster_group_config_page.config.save_config()
            assert not cluster_group_config_page.is_popup_presented_on_page(), "No popup should be shown after save"

    def test_config_save_advanced(self, app_fs, sdk_client_fs, create_cluster):
        """Test to check config save with ui option advanced"""
        with allure.step("Create cluster and service"):
            cluster = create_cluster
            service = cluster.service_add(name="service_advanced")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()

        with allure.step("Check config ui option advanced"):
            self.check_advanced_params(service_config_page)
            self._save_config_and_refresh(service_config_page)
            self.check_advanced_params(service_config_page)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()
            cluster_group_config_page.config.set_description(self.CONFIG_NAME_NEW)

        with allure.step("Save group config and check that popup is not presented on page"):
            cluster_group_config_page.config.save_config()
            assert not cluster_group_config_page.is_popup_presented_on_page(), "No popup should be shown after save"

    def test_config_save_read_only(self, app_fs, sdk_client_fs, create_cluster):
        """Test to check config save with ui option advanced"""
        with allure.step("Create cluster and service"):
            cluster = create_cluster
            service = cluster.service_add(name="service_read_only")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()

        with allure.step("Check config read_only options after save"):
            self._check_read_only_params(service_config_page)
            string_row, *_ = service_config_page.config.get_all_config_rows()
            service_config_page.config.type_in_field_with_few_inputs(
                string_row, [self.CHANGE_STRUCTURE_COUNTRY], clear=True
            )
            service_config_page.config.save_config()
            service_config_page.config.driver.refresh()
            service_config_page.config.assert_input_value_is(
                expected_value=self.CHANGE_STRUCTURE_COUNTRY, display_name="string"
            )

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()

        with allure.step("Change writable param and click save button"):
            cluster_group_config_page.config.assert_input_value_is(
                expected_value=self.CHANGE_STRUCTURE_COUNTRY, display_name="string"
            )
            string_row, *_ = service_config_page.config.get_all_config_rows()
            cluster_group_config_page.group_config.click_on_customization_chbx(string_row)
            cluster_group_config_page.config.type_in_field_with_few_inputs(
                string_row, [self.STRING_ROW_NAME], clear=True
            )

        with allure.step("Save group config and check row"):
            service_config_page.config.save_config()
            service_config_page.config.driver.refresh()
            cluster_group_config_page.config.assert_input_value_is(
                expected_value=self.STRING_ROW_NAME, display_name="string"
            )

    def test_config_save_schema_dict(self, app_fs, sdk_client_fs, create_cluster):
        """Test to check config save"""
        with allure.step("Create cluster and service"):
            cluster = create_cluster
            service = cluster.service_add(name="service_config_schema_dict")

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()

        with allure.step("Add params to group config and save"):
            _, structure_row, *_ = cluster_group_config_page.group_config.get_all_group_config_rows()
            cluster_group_config_page.group_config.click_on_customization_chbx(structure_row)
            structure_params = [self.CHANGE_STRUCTURE_CODE, self.CHANGE_STRUCTURE_COUNTRY]
            for i in range(3):
                cluster_group_config_page.config.click_add_item_btn_in_row(self.STRUCTURE_ROW_NAME)
                structure_params.extend((f"{self.CHANGE_STRUCTURE_COUNTRY}-{i}", self.CHANGE_STRUCTURE_CODE + i))
            cluster_group_config_page.config.type_in_field_with_few_inputs(
                self.STRUCTURE_ROW_NAME, structure_params, clear=True
            )
            self._save_config_and_refresh(cluster_group_config_page)

        with allure.step("Check group config params after save"):
            cluster_group_config_page.config.assert_map_value_is(
                expected_value=self.STRUCTURE_LIST, display_name=self.STRUCTURE_ROW_NAME
            )

    def test_config_group(self, app_fs, sdk_client_fs, create_cluster):
        """Test to check config save"""
        with allure.step("Create cluster and service"):
            cluster = create_cluster
            service = cluster.service_add(name="service_config_default")

        with allure.step("Create service config"):
            service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_config_page.config.set_description(self.CONFIG_NAME_NEW)
            self._save_config_and_refresh(service_config_page)
            service_config_page.config.compare_versions(self.CONFIG_NAME_OLD)

        with allure.step("Create group config"):
            service_group_config = service.group_config_create("service-group")
            cluster_group_config_page = ClusterGroupConfigConfig(
                app_fs.driver, app_fs.adcm.url, cluster.id, service_group_config.id
            ).open()

        with allure.step("Change structure params in group config and disable customization checkbox"):
            _, structure_row, *_ = cluster_group_config_page.group_config.get_all_group_config_rows()
            cluster_group_config_page.group_config.click_on_customization_chbx(structure_row)
            cluster_group_config_page.config.type_in_field_with_few_inputs(
                structure_row, [self.CHANGE_STRUCTURE_CODE], clear=True
            )
            cluster_group_config_page.group_config.click_on_customization_chbx(structure_row)

        with allure.step("Check popup message when saving"):
            service_config_page.config.save_config()
            assert service_config_page.is_popup_presented_on_page(), "Popup should be shown with try to save"
