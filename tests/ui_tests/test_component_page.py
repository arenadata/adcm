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

# pylint: disable=redefined-outer-name,unused-argument

"""UI tests for /cluster page"""

import os
from typing import Tuple

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Host, Service
from adcm_pytest_plugin import utils
from tests.library.status import ADCMObjectStatusChanger
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.common.configuration.page import CONFIG_ITEMS
from tests.ui_tests.app.page.common.group_config_list.page import GroupConfigRowInfo
from tests.ui_tests.app.page.common.status.page import (
    NEGATIVE_COLOR,
    SUCCESS_COLOR,
    StatusRowInfo,
)
from tests.ui_tests.app.page.component.page import (
    ComponentConfigPage,
    ComponentGroupConfigPage,
    ComponentMainPage,
    ComponentStatusPage,
)
from tests.ui_tests.app.page.host.page import HostStatusPage
from tests.ui_tests.app.page.service.page import ServiceComponentPage
from tests.ui_tests.utils import create_few_groups

BUNDLE_COMMUNITY = "cluster_community"
COMPONENT_WITH_REQUIRED_FIELDS = "component_with_required_string"
COMPONENT_WITH_DESCRIPTION_FIELDS = "component_with_all_config_params"
COMPONENT_WITH_DEFAULT_FIELDS = "component_with_default_string"
CLUSTER_NAME = "Test cluster"
SERVICE_NAME = "test_service"
PROVIDER_NAME = 'test_provider'
PROVIDER_BUNDLE = 'provider'
HOST_NAME = 'test-host'
FIRST_COMPONENT_NAME = "first"
SECOND_COMPONENT_NAME = "second"

pytestmark = pytest.mark.usefixtures("_login_to_adcm_over_api")


# !===== Fixtures =====!


@pytest.fixture()
def create_cluster_with_service(sdk_client_fs: ADCMClient, bundle_archive: str) -> Tuple[Cluster, Service]:
    """Create cluster with service"""

    cluster_bundle = sdk_client_fs.upload_from_fs(bundle_archive)
    cluster = cluster_bundle.cluster_create(name=CLUSTER_NAME)
    service = cluster.service_add(name=SERVICE_NAME)
    return cluster, service


@pytest.fixture()
def create_cluster_with_hostcomponents(
    create_cluster_with_service: Tuple[Cluster, Service], sdk_client_fs: ADCMClient
) -> Tuple[Cluster, Service, Host]:
    """Create cluster with component"""

    cluster, service = create_cluster_with_service
    provider_bundle = sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), PROVIDER_BUNDLE))
    provider = provider_bundle.provider_create(PROVIDER_NAME)
    host = provider.host_create(HOST_NAME)
    cluster.host_add(host)
    cluster.hostcomponent_set((host, service.component(name=FIRST_COMPONENT_NAME)))
    return cluster, service, host


# !===== Tests =====!


@pytest.mark.parametrize("bundle_archive", [utils.get_data_dir(__file__, BUNDLE_COMMUNITY)], indirect=True)
class TestComponentMainPage:
    """Tests for the /cluster/{}/service/{}/component/{}/ page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_by_tab_main_component_page(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/component/{}/main page from left menu"""

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_config_page = ComponentConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_main_page = component_config_page.open_main_tab()
        component_main_page.check_all_elements()
        component_main_page.check_component_toolbar(CLUSTER_NAME, SERVICE_NAME, FIRST_COMPONENT_NAME)

    def test_open_by_toolbar_admin_page(self, app_fs, create_cluster_with_service):
        """Test open admin/intro page from component toolbar"""

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_main_page = ComponentMainPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_main_page.toolbar.click_admin_link()
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_open_by_toolbar_main_component_page(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/component/{}/main page from toolbar"""

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_config_page = ComponentConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_config_page.click_link_by_name(FIRST_COMPONENT_NAME)
        component_main_page = ComponentMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id)
        component_main_page.wait_page_is_opened()
        component_main_page.check_component_toolbar(CLUSTER_NAME, SERVICE_NAME, FIRST_COMPONENT_NAME)

    def test_open_by_toolbar_main_component_list_page(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/component page from toolbar"""

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_main_page = ComponentMainPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_main_page.click_link_by_name("COMPONENTS")
        service_comp_page = ServiceComponentPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id)
        service_comp_page.wait_page_is_opened()
        service_comp_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)


class TestComponentConfigPage:
    """Tests for the /cluster/{}/service/{}/component/{}/config page"""

    @pytest.mark.parametrize("bundle_archive", [utils.get_data_dir(__file__, BUNDLE_COMMUNITY)], indirect=True)
    def test_open_by_tab_config_component_page(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/component/{}/config from left menu"""

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_main_page = ComponentMainPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_config_page = component_main_page.open_config_tab()
        component_config_page.check_all_elements()
        component_config_page.check_component_toolbar(CLUSTER_NAME, SERVICE_NAME, FIRST_COMPONENT_NAME)

    @pytest.mark.parametrize("bundle_archive", [utils.get_data_dir(__file__, BUNDLE_COMMUNITY)], indirect=True)
    def test_filter_config_on_component_config_page(self, app_fs, create_cluster_with_service):
        """Test config filtration on /cluster/{}/service/{}/component/{}/config page"""

        params = {"search_param": "str_param", "group_name": "core-site"}

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_config_page = ComponentConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        with component_config_page.config.wait_rows_change():
            component_config_page.config.search(params["search_param"])
        with allure.step(f"Check that rows are filtered by {params['search_param']}"):
            config_rows = component_config_page.config.get_all_config_rows()
            assert len(config_rows) == 1, "Rows are not filtered: there should be 1 row"
            assert (
                component_config_page.config.get_config_row_info(config_rows[0]).name == f"{params['search_param']}:"
            ), f"Name should be {params['search_param']}"
        with component_config_page.config.wait_rows_change():
            component_config_page.config.clear_search_input()
        with allure.step("Check that rows are not filtered"):
            config_rows = component_config_page.config.get_all_config_rows()
            assert len(config_rows) == 5, "Rows are filtered: there should be 4 row and 1 config group"
        with component_config_page.config.wait_rows_change(expected_rows_amount=3):
            component_config_page.config.click_on_group(params["group_name"])

    @pytest.mark.parametrize(
        "bundle_archive", [utils.get_data_dir(__file__, COMPONENT_WITH_DESCRIPTION_FIELDS)], indirect=True
    )
    def test_save_custom_config_on_component_config_page(
        self, app_fs, create_cluster_with_service, create_bundle_archives
    ):
        """Test config save on /cluster/{}/service/{}/component/{}/config page"""

        params = {
            "config_name_new": "test_name",
            "config_name_old": "init",
        }

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_config_page = ComponentConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_config_page.config.fill_config_fields_with_test_values()
        component_config_page.config.set_description(params["config_name_new"])
        component_config_page.config.save_config()
        component_config_page.config.compare_versions(params["config_name_old"])
        component_config_page.config.check_config_fields_history_with_test_values()

    @pytest.mark.parametrize("bundle_archive", [utils.get_data_dir(__file__, BUNDLE_COMMUNITY)], indirect=True)
    def test_reset_config_in_row_on_component_config_page(self, app_fs, create_cluster_with_service):
        """Test config reset on /cluster/{}/service/{}/component/{}/config page"""

        params = {"row_name": "str_param", "row_value_new": "test", "row_value_old": "123", "config_name": "test_name"}

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_config_page = ComponentConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        config_row = component_config_page.config.get_all_config_rows()[0]
        component_config_page.config.type_in_field_with_few_inputs(
            row=config_row, values=[params["row_value_new"]], clear=True
        )
        component_config_page.config.set_description(params["config_name"])
        component_config_page.config.save_config()

        config_row = component_config_page.config.get_all_config_rows()[0]
        component_config_page.config.reset_to_default(row=config_row)
        component_config_page.config.assert_input_value_is(
            expected_value=params["row_value_old"], display_name=params["row_name"]
        )

    @pytest.mark.parametrize(
        "bundle_archive", [utils.get_data_dir(__file__, COMPONENT_WITH_REQUIRED_FIELDS)], indirect=True
    )
    def test_field_validation_on_component_config_page(
        self, app_fs, create_cluster_with_service, create_bundle_archives
    ):
        """Test config fields validation on /cluster/{}/service/{}/component/{}/config page"""
        params = {
            'pass_name': 'Important password',
            'req_name': 'Required item',
            'not_req_name': 'Just item',
            'wrong_value': 'test',
        }
        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_config_page = ComponentConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_config_page.config.check_password_confirm_required(params['pass_name'])
        component_config_page.config.check_field_is_required(params['req_name'])
        config_row = component_config_page.config.get_all_config_rows()[0]
        component_config_page.config.type_in_field_with_few_inputs(row=config_row, values=[params['wrong_value']])
        component_config_page.config.check_field_is_invalid(params['not_req_name'])
        component_config_page.config.check_config_warn_icon_on_left_menu()
        component_config_page.toolbar.check_warn_button(
            tab_name=FIRST_COMPONENT_NAME, expected_warn_text=[f'{FIRST_COMPONENT_NAME} has an issue with its config']
        )

    @pytest.mark.parametrize(
        "bundle_archive", [utils.get_data_dir(__file__, COMPONENT_WITH_DEFAULT_FIELDS)], indirect=True
    )
    def test_field_validation_on_component_config_page_with_default_value(
        self, app_fs, create_cluster_with_service, create_bundle_archives
    ):
        """Test config fields validation on /cluster/{}/service/{}/component/{}/config page"""

        params = {'field_name': 'string', 'new_value': 'test', "config_name": "test_name"}

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_config_page = ComponentConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_config_page.config.clear_field_by_keys(params['field_name'])
        component_config_page.config.check_field_is_required(params['field_name'])
        component_config_page.config.type_in_field_with_few_inputs(
            row=component_config_page.config.get_all_config_rows()[0], values=[params['new_value']]
        )
        component_config_page.config.save_config()
        component_config_page.config.assert_input_value_is(
            expected_value=params["new_value"], display_name=params["field_name"]
        )

    @pytest.mark.parametrize(
        "bundle_archive", [utils.get_data_dir(__file__, COMPONENT_WITH_DESCRIPTION_FIELDS)], indirect=True
    )
    def test_field_tooltips_on_component_config_page(self, app_fs, create_cluster_with_service, create_bundle_archives):
        """Test config fields tooltips on /cluster/{}/service/{}/component/{}/config page"""

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_config_page = ComponentConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        for item in CONFIG_ITEMS:
            component_config_page.config.check_text_in_tooltip(item, f"Test description {item}")


@pytest.mark.parametrize("bundle_archive", [utils.get_data_dir(__file__, BUNDLE_COMMUNITY)], indirect=True)
class TestComponentGroupConfigPage:
    """Tests for the /cluster/{}/service/{}/component/{}/group_config page"""

    def test_open_by_tab_group_config_component_page(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/component/{}/group_config from left menu"""

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_main_page = ComponentMainPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_groupconf_page = component_main_page.open_group_config_tab()
        component_groupconf_page.check_all_elements()
        component_groupconf_page.check_component_toolbar(CLUSTER_NAME, SERVICE_NAME, FIRST_COMPONENT_NAME)

    def test_create_group_config_component(self, app_fs, create_cluster_with_service):
        """Test create group config on /cluster/{}/service/{}/component/{}/group_config"""

        params = {
            'name': 'Test name',
            'description': 'Test description',
        }

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_group_conf_page = ComponentGroupConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        with component_group_conf_page.group_config.wait_rows_change(expected_rows_amount=1):
            component_group_conf_page.group_config.create_group(name=params['name'], description=params['description'])
        group_row = component_group_conf_page.group_config.get_all_config_rows()[0]
        with allure.step("Check created row in component"):
            group_info = component_group_conf_page.group_config.get_config_row_info(group_row)
            assert group_info == GroupConfigRowInfo(
                name=params['name'], description=params['description']
            ), "Row value differs in component groups"
        with component_group_conf_page.group_config.wait_rows_change(expected_rows_amount=0):
            component_group_conf_page.group_config.delete_row(group_row)

    def test_check_pagination_on_group_config_component_page(self, app_fs, create_cluster_with_service):
        """Test pagination on /cluster/{}/service/{}/component/{}/group_config page"""

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        group_conf_page = ComponentGroupConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        create_few_groups(group_conf_page.group_config)
        group_conf_page.table.check_pagination(second_page_item_amount=1)


@pytest.mark.parametrize("bundle_archive", [utils.get_data_dir(__file__, BUNDLE_COMMUNITY)], indirect=True)
class TestComponentStatusPage:
    """Tests for the /cluster/{}/service/{}/component/{}/status page"""

    def test_open_by_tab_status_component_page(self, app_fs, create_cluster_with_service):
        """Test open /cluster/{}/service/{}/component/{}/status page from left menu"""

        cluster, service = create_cluster_with_service
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_config_page = ComponentConfigPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_status_page = component_config_page.open_status_tab()
        component_status_page.check_all_elements()
        component_status_page.check_component_toolbar(CLUSTER_NAME, SERVICE_NAME, FIRST_COMPONENT_NAME)

    def test_status_on_component_status_page(self, app_fs, adcm_fs, sdk_client_fs, create_cluster_with_hostcomponents):
        """Changes status on /cluster/{}/service/{}/component/{}/status"""

        success_status = [
            StatusRowInfo(
                icon_status=True, group_name='first', state='successful 1/1', state_color=SUCCESS_COLOR, link=None
            ),
            StatusRowInfo(icon_status=True, group_name=None, state=None, state_color=None, link='test-host'),
        ]
        negative_status = [
            StatusRowInfo(
                icon_status=False, group_name='first', state='successful 0/1', state_color=NEGATIVE_COLOR, link=None
            ),
            StatusRowInfo(icon_status=False, group_name=None, state=None, state_color=None, link='test-host'),
        ]

        cluster, service, host = create_cluster_with_hostcomponents
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_status_page = ComponentStatusPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        status_changer = ADCMObjectStatusChanger(sdk_client_fs, adcm_fs)
        with allure.step("Check positive status on component"):
            status_changer.enable_cluster(cluster)
            component_status_page.driver.refresh()
            component_status_page.compare_current_and_expected_state(success_status)
        with allure.step("Check negative status on component"):
            status_changer.set_component_negative_status((host, component))
            component_status_page.driver.refresh()
            component_status_page.compare_current_and_expected_state(negative_status)
        with allure.step("Check collapse button"):
            with component_status_page.wait_rows_collapsed():
                component_status_page.click_collapse_all_btn()
            assert len(component_status_page.get_all_rows()) == 1, "Status rows should have been collapsed"

    def test_link_to_host_on_component_status_page(
        self, app_fs, adcm_fs, sdk_client_fs, create_cluster_with_hostcomponents
    ):
        """Check that host link points to the host page"""

        cluster, service, host = create_cluster_with_hostcomponents
        component = service.component(name=FIRST_COMPONENT_NAME)
        component_status_page = ComponentStatusPage(
            app_fs.driver, app_fs.adcm.url, cluster.id, service.id, component.id
        ).open()
        component_status_page.click_host_by_name(host.fqdn)
        HostStatusPage(app_fs.driver, app_fs.adcm.url, host.id, None).wait_page_is_opened()
