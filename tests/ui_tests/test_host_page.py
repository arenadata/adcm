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

# pylint: disable=redefined-outer-name

"""UI tests for /host page"""

import os
from typing import Tuple

import allure
import pytest
from _pytest.fixtures import SubRequest
from adcm_client.objects import ADCMClient, Bundle, Cluster, Host, Provider
from adcm_pytest_plugin import utils
from selenium.common import StaleElementReferenceException
from tests.library.retry import RetryFromCheckpoint, Step
from tests.library.status import ADCMObjectStatusChanger
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CONFIG_ITEMS
from tests.ui_tests.app.page.common.status.page import (
    NEGATIVE_COLOR,
    SUCCESS_COLOR,
    StatusRowInfo,
)
from tests.ui_tests.app.page.host.locators import HostLocators
from tests.ui_tests.app.page.host.page import (
    HostConfigPage,
    HostMainPage,
    HostStatusPage,
)
from tests.ui_tests.app.page.host_list.locators import HostListLocators
from tests.ui_tests.app.page.host_list.page import HostListPage
from tests.ui_tests.utils import expect_rows_amount_change, wait_and_assert_ui_info

# defaults
HOST_FQDN = 'best-host'
CLUSTER_NAME = 'Best Cluster Ever'
PROVIDER_NAME = 'Black Mark'

INIT_ACTION = 'Init'
REINIT_ACTION = "Reinit"

# config fields
REGULAR_FIELD_NAME = 'Just item'
REQUIRED_FIELD_NAME = 'Required item'
PASSWORD_FIELD_NAME = 'Important password'
SECRETTEXT_FIELD_NAME = 'secrettext'
ADVANCED_FIELD_NAME = 'Advanced option'


# !===== Fixtures =====!


@pytest.fixture(params=["provider"])
@allure.title("Upload provider bundle")
def provider_bundle(request: SubRequest, sdk_client_fs: ADCMClient) -> Bundle:
    """Upload provider bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), request.param))


@allure.title("Create provider")
@pytest.fixture()
def upload_and_create_provider(provider_bundle) -> Tuple[Bundle, Provider]:
    """Create provider"""
    provider = provider_bundle.provider_create(PROVIDER_NAME)
    return provider_bundle, provider


@pytest.fixture()
@allure.title("Create host")
def create_host(upload_and_create_provider: Tuple[Bundle, Provider]):
    """Create default host using API"""
    provider = upload_and_create_provider[1]
    return provider.host_create(HOST_FQDN)


@pytest.fixture()
@allure.title("Create many hosts")
def _create_many_hosts(request, upload_and_create_provider):
    """Pass amount in param"""
    provider = upload_and_create_provider[1]
    for i in range(request.param):
        provider.host_create(f'no-fantasy-{i}')


@pytest.fixture()
def create_bonded_host(
    upload_and_create_cluster: Tuple[Bundle, Cluster],
    upload_and_create_provider: Tuple[Bundle, Provider],
):
    """Create host bonded to cluster"""
    provider = upload_and_create_provider[1]
    host = provider.host_create(HOST_FQDN)
    cluster = upload_and_create_cluster[1]
    cluster.host_add(host)
    return cluster, host


@pytest.fixture()
@allure.title("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient) -> Bundle:
    """Upload cluster bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), "cluster"))


@pytest.fixture()
@allure.title("Create cluster")
def upload_and_create_cluster(cluster_bundle: Bundle) -> Tuple[Bundle, Cluster]:
    """Create cluster"""
    cluster = cluster_bundle.cluster_prototype().cluster_create(CLUSTER_NAME)
    return cluster_bundle, cluster


@pytest.fixture()
@allure.title("Open /host page")
def page(app_fs: ADCMTest, _login_to_adcm_over_api) -> HostListPage:
    """Open host page"""
    return HostListPage(app_fs.driver, app_fs.adcm.url).open()


@allure.step('Open host config menu from host list')
def open_config(page) -> HostConfigPage:
    """'Open host config menu from host list'"""
    page.click_on_row_child(0, HostListLocators.HostTable.HostRow.config)
    return HostConfigPage(page.driver, page.base_url, 1, None)


def _check_job_name(sdk: ADCMClient, action_display_name: str):
    """Check job with correct name is launched"""
    jobs_display_names = {job.display_name for job in sdk.job_list()}
    assert action_display_name in jobs_display_names, (
        f'Action with name "{action_display_name}" was not ran. ' f'Job names found: {jobs_display_names}'
    )


def _check_menu(
    menu_name: str,
    provider: Provider,
    list_page: HostListPage,
):
    list_page.click_on_row_child(0, HostListLocators.HostTable.HostRow.fqdn)
    host_page = HostMainPage(list_page.driver, list_page.base_url, 1, None)
    getattr(host_page, f'open_{menu_name}_tab')()
    host_page.check_fqdn_equal_to(HOST_FQDN)
    bundle_label = host_page.get_bundle_label()
    # Test Host is name of host in config.yaml
    assert provider.name == bundle_label


# !===== TESTS =====!


class TestHostListPage:
    """Tests for the /host page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize(
        "bundle_archive",
        [utils.get_data_dir(__file__, "provider")],
        indirect=True,
        ids=['provider_bundle'],
    )
    def test_create_host_with_bundle_upload(self, page: HostListPage, bundle_archive: str):
        """Upload bundle and create host"""

        host_fqdn = 'howdy-host-fqdn'
        page.open_host_creation_popup()
        new_provider_name = page.host_popup.create_provider_and_host(bundle_archive, host_fqdn)
        expected_values = {
            'fqdn': host_fqdn,
            'provider': new_provider_name,
            'cluster': None,
            'state': 'created',
        }
        wait_and_assert_ui_info(
            expected_values,
            page.get_host_info_from_row,
        )

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.usefixtures("upload_and_create_provider", "upload_and_create_cluster")
    def test_create_bonded_to_cluster_host(self, page: HostListPage):
        """Create host bonded to cluster"""

        host_fqdn = 'cluster-host'
        expected_values = {
            'fqdn': host_fqdn,
            'provider': PROVIDER_NAME,
            'cluster': CLUSTER_NAME,
            'state': 'created',
        }
        self._create_host_bonded_to_cluster(page, host_fqdn)
        wait_and_assert_ui_info(
            expected_values,
            page.get_host_info_from_row,
            timeout=10,
        )

    @staticmethod
    def _create_host_bonded_to_cluster(page: HostListPage, fqdn: str) -> None:
        host_bonding_retry = RetryFromCheckpoint(
            execution_steps=[
                Step(page.open_host_creation_popup),
                Step(page.host_popup.create_host, [fqdn], {"cluster": CLUSTER_NAME}),
            ],
            restoration_steps=[
                Step(page.driver.refresh),
                Step(page.open_host_creation_popup),
            ],
        )
        with allure.step("Try to bound host to cluster during new host creation"):
            host_bonding_retry(restore_from=(AssertionError, TimeoutError, StaleElementReferenceException))

    @pytest.mark.parametrize("_create_many_hosts", [12], indirect=True)
    @pytest.mark.usefixtures("_create_many_hosts")
    def test_host_list_pagination(self, page: HostListPage):
        """Create more than 10 hosts and check pagination"""

        hosts_on_second_page = 2
        page.close_info_popup()
        page.table.check_pagination(hosts_on_second_page)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.usefixtures("upload_and_create_provider", "upload_and_create_cluster")
    def test_bind_host_to_cluster(self, page: HostListPage):
        """Create host and go to cluster from host list"""

        expected_values = {
            'fqdn': HOST_FQDN,
            'provider': PROVIDER_NAME,
            'cluster': None,
            'state': 'created',
        }
        page.open_host_creation_popup()
        page.host_popup.create_host(HOST_FQDN)
        with allure.step("Check host is created and isn't bound to a cluster"):
            wait_and_assert_ui_info(
                expected_values,
                page.get_host_info_from_row,
            )
        page.bind_host_to_cluster(0, CLUSTER_NAME)
        page.assert_host_bonded_to_cluster(0, CLUSTER_NAME)

    @pytest.mark.parametrize(
        ('row_child_name', 'menu_item_name'),
        [
            pytest.param(
                'fqdn', 'main_tab', id='open_host_tab', marks=[pytest.mark.smoke, pytest.mark.include_firefox()]
            ),
            pytest.param('status', 'status_tab', id='open_status_tab'),
            pytest.param('config', 'config_tab', id='open_config_tab'),
        ],
    )
    @pytest.mark.usefixtures('create_host')
    def test_open_host_from_host_list(self, page: HostListPage, row_child_name: str, menu_item_name: str):
        """Test open host page from host list"""

        row_child = getattr(HostListLocators.HostTable.HostRow, row_child_name)
        menu_item_locator = getattr(HostLocators.MenuNavigation, menu_item_name)
        page.click_on_row_child(0, row_child)
        main_host_page = HostMainPage(page.driver, page.base_url, 1, None)
        with allure.step('Check correct menu is opened'):
            main_host_page.check_fqdn_equal_to(HOST_FQDN)
            assert main_host_page.active_menu_is(menu_item_locator)
            main_host_page.check_host_toolbar(HOST_FQDN)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.usefixtures("create_host", "upload_and_create_provider")
    def test_delete_host(self, page: HostListPage):
        """Create host and delete it"""

        expected_values = {
            'fqdn': HOST_FQDN,
            'provider': PROVIDER_NAME,
            'cluster': None,
            'state': 'created',
        }
        wait_and_assert_ui_info(expected_values, page.get_host_info_from_row)
        page.delete_host(0)
        page.check_element_should_be_hidden(HostListLocators.HostTable.row)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_delete_bonded_host(self, page: HostListPage, create_bonded_host):
        """Host shouldn't be deleted"""

        page.check_element_should_be_visible(HostListLocators.HostTable.row)
        page.open_host_creation_popup()
        page.host_popup.create_host(HOST_FQDN, cluster=CLUSTER_NAME)
        page.delete_host(0)
        page.check_element_should_be_visible(HostListLocators.HostTable.row)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize('menu', ['main', 'config', 'status'])
    @pytest.mark.usefixtures('create_host')
    def test_open_menu(self, upload_and_create_provider: Tuple[Bundle, Provider], page: HostListPage, menu: str):
        """Open detailed host page and open menu from side navigation"""

        _, provider = upload_and_create_provider
        _check_menu(menu, provider, page)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.usefixtures('create_host')
    def test_run_action_on_new_host(self, page: HostListPage):
        """Create host and run action on it"""

        page.assert_host_state(0, 'created')
        page.run_action(0, INIT_ACTION)
        page.assert_host_state(0, 'running')

    @pytest.mark.smoke()
    def test_maintenance_mode_on_host_page(self, page: HostListPage, create_bonded_host):
        """Test maintenance mode on host page"""

        cluster, host = create_bonded_host
        page.driver.refresh()
        with allure.step("Check that mm is not available after removing from cluster with ON state"):
            page.assert_maintenance_mode_state(0)
            cluster.host_delete(host)
            page.driver.refresh()
            page.assert_maintenance_mode_state(0, None)
        with allure.step("Check that mm is not available after removing from cluster with OFF state"):
            cluster.host_add(host)
            page.driver.refresh()
            page.click_on_maintenance_mode_btn(0)
            cluster.host_delete(host)
            page.driver.refresh()
            page.assert_maintenance_mode_state(0, None)

    @pytest.mark.smoke()
    def test_action_with_maintenance_mode_on_host_page(self, sdk_client_fs, page: HostListPage, create_bonded_host):
        """Test maintenance mode on host page"""

        with allure.step("Turn ON maintenance mode"):
            page.driver.refresh()
            page.click_on_maintenance_mode_btn(0)
        with allure.step("Check actions are displayed"):
            assert page.get_enabled_action_names(0) == [
                INIT_ACTION
            ], f"Action list with MM ON should be with action {INIT_ACTION}"
            assert page.get_disabled_action_names(0) == [], "There should be 0 disabled actions"
        with allure.step("Run action and check available actions changed"):
            page.run_action(0, INIT_ACTION)
            _ = [job.wait() for job in sdk_client_fs.job_list()]
            page.header.wait_success_job_amount_from_header(1)
            page.driver.refresh()
            assert page.get_disabled_action_names(0) == [
                REINIT_ACTION
            ], f"Action {REINIT_ACTION} should be shown and disabled in new state"
            assert page.get_enabled_action_names(0) == [], "There should be 0 enabled actions"
        with allure.step("Turn ON maintenance mode and check actions"):
            page.click_on_maintenance_mode_btn(0)
            assert page.get_enabled_action_names(0) == [
                REINIT_ACTION
            ], f"Action list with MM ON should be with action {REINIT_ACTION}"


@pytest.mark.usefixtures('_login_to_adcm_over_api')
class TestHostMainPage:
    """Tests for the /host/{}/config page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_by_tab_host_main_page(self, app_fs, create_host):
        """Test open /host/{}/main page from left menu"""

        host_config_page = HostConfigPage(app_fs.driver, app_fs.adcm.url, create_host.host_id).open()
        host_main_page = host_config_page.open_main_tab()
        host_main_page.check_all_elements()
        host_main_page.check_host_toolbar(HOST_FQDN)

    def test_check_host_admin_page_open_by_toolbar(self, app_fs, create_host):
        """Test open admin/intro page from host toolbar"""

        host_main_page = HostMainPage(app_fs.driver, app_fs.adcm.url, create_host.host_id).open()
        host_main_page.toolbar.click_admin_link()
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_check_host_main_page_open_by_toolbar(self, app_fs, create_host):
        """Test open /host/{}/main page from host toolbar"""

        params = {"host_list_name": "HOSTS"}

        host_main_page = HostMainPage(app_fs.driver, app_fs.adcm.url, create_host.host_id).open()
        host_main_page.toolbar.click_link_by_name(params["host_list_name"])
        HostListPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
        host_main_page = HostMainPage(app_fs.driver, app_fs.adcm.url, create_host.host_id).open()
        host_main_page.toolbar.click_link_by_name(HOST_FQDN)
        host_main_page.wait_page_is_opened()
        host_main_page.check_host_toolbar(HOST_FQDN)

    def test_check_cluster_run_action_on_host_page_by_toolbar(self, app_fs, create_host):
        """Test run action from the /cluster/{}/main page toolbar"""

        params = {"action_name": "Init"}

        host_main_page = HostMainPage(app_fs.driver, app_fs.adcm.url, create_host.host_id).open()
        host_main_page.toolbar.run_action(HOST_FQDN, params["action_name"])
        with allure.step("Check success job"):
            assert (
                host_main_page.header.get_in_progress_job_amount_from_header() == "1"
            ), "There should be 1 in progress job in header"


class TestHostConfigPage:
    """Tests for the /host/{}/config page"""

    @pytest.mark.parametrize('provider_bundle', ["provider_config"], indirect=True)
    @pytest.mark.usefixtures('create_host')
    def test_filter_config(self, page: HostListPage):
        """Use filters on host configuration page"""

        params = {'group': 'group_one', 'search_text': 'Adv'}
        host_page = open_config(page)
        host_page.check_host_toolbar(HOST_FQDN)
        get_rows_func = host_page.config.get_all_config_rows
        with allure.step('Check unfiltered configuration'):
            host_page.config.check_config_fields_visibility(
                {REGULAR_FIELD_NAME, REQUIRED_FIELD_NAME, PASSWORD_FIELD_NAME}, {ADVANCED_FIELD_NAME}
            )
        with allure.step('Check group roll up'):
            with expect_rows_amount_change(get_rows_func):
                host_page.config.click_on_group(params['group'])
            host_page.config.check_config_fields_visibility(
                {PASSWORD_FIELD_NAME}, {REGULAR_FIELD_NAME, REQUIRED_FIELD_NAME}
            )
            with expect_rows_amount_change(get_rows_func):
                host_page.config.click_on_group(params['group'])
            host_page.config.check_config_fields_visibility({REGULAR_FIELD_NAME})
        with allure.step('Check configuration with "Advanced" turned on'):
            with expect_rows_amount_change(get_rows_func):
                host_page.find_and_click(CommonConfigMenu.advanced_label)
            host_page.config.check_config_fields_visibility(
                {ADVANCED_FIELD_NAME, REGULAR_FIELD_NAME, REQUIRED_FIELD_NAME, PASSWORD_FIELD_NAME}
            )
        with allure.step('Check search filtration'):
            with expect_rows_amount_change(get_rows_func):
                host_page.config.search(params['search_text'])
            host_page.config.check_config_fields_visibility(
                {ADVANCED_FIELD_NAME}, {REGULAR_FIELD_NAME, REQUIRED_FIELD_NAME, PASSWORD_FIELD_NAME}
            )
            with expect_rows_amount_change(get_rows_func):
                host_page.find_and_click(CommonConfigMenu.advanced_label)
            host_page.config.check_config_fields_visibility(set(), {ADVANCED_FIELD_NAME})

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize('provider_bundle', ["host_with_all_config_params"], indirect=True)
    @pytest.mark.usefixtures('create_host')
    def test_custom_name_config(self, page: HostListPage):
        """Change configuration, save with custom name, compare changes"""

        params = {
            "config_name_new": "test_name",
            "config_name_old": "init",
        }
        host_page = open_config(page)
        host_page.check_host_toolbar(HOST_FQDN)
        host_page.close_info_popup()
        host_page.config.fill_config_fields_with_test_values()
        host_page.config.set_description(params["config_name_new"])
        host_page.config.save_config()
        host_page.config.compare_versions(params["config_name_old"])
        host_page.config.check_config_fields_history_with_test_values()

    @pytest.mark.parametrize('provider_bundle', ["provider_config"], indirect=True)
    @pytest.mark.usefixtures('create_host')
    def test_reset_configuration(self, page: HostListPage):
        """Change configuration, save, reset to defaults"""
        params = {
            'password': 'pass',
            'type_in_req_field': '42',
            'init_value': '',
        }
        host_page = open_config(page)
        host_page.config.type_in_field_with_few_inputs(
            row=host_page.config.get_config_row(PASSWORD_FIELD_NAME),
            values=[params['password'], params['password']],
            clear=True,
        )
        host_page.config.type_in_field_with_few_inputs(
            row=host_page.config.get_config_row(REQUIRED_FIELD_NAME), values=[params['type_in_req_field']], clear=True
        )
        host_page.config.save_config()
        host_page.config.reset_to_default(host_page.config.get_config_row(REQUIRED_FIELD_NAME))
        host_page.config.assert_input_value_is(params['init_value'], REQUIRED_FIELD_NAME)
        host_page.config.reset_to_default(host_page.config.get_config_row(PASSWORD_FIELD_NAME))
        host_page.config.assert_input_value_is(
            params['init_value'],
            PASSWORD_FIELD_NAME,
            is_password=True,
        )

    @pytest.mark.parametrize('provider_bundle', ["provider_config"], indirect=True)
    @pytest.mark.usefixtures('create_host')
    def test_field_validation(self, page: HostListPage):
        """Inputs are validated correctly"""
        wrong_value = 'etonechislo'
        host_page = open_config(page)
        regular_row = host_page.config.get_config_row(REGULAR_FIELD_NAME)
        host_page.config.check_password_confirm_required(PASSWORD_FIELD_NAME)
        host_page.config.check_field_is_required(REQUIRED_FIELD_NAME)
        host_page.config.type_in_field_with_few_inputs(row=regular_row, values=[wrong_value])
        host_page.config.check_field_is_invalid(REGULAR_FIELD_NAME)
        host_page.config.check_config_warn_icon_on_left_menu()
        host_page.toolbar.check_warn_button(
            tab_name=HOST_FQDN, expected_warn_text=[f'{HOST_FQDN} has an issue with its config']
        )

    @pytest.mark.parametrize('provider_bundle', ["host_with_default_string"], indirect=True)
    @pytest.mark.usefixtures('create_host')
    def test_field_validation_on_host_config_page_with_default_value(self, page: HostListPage):
        """Test config fields validation on host config page"""

        params = {'field_name': 'string', 'new_value': 'test', "config_name": "test_name"}

        host_page = open_config(page)
        host_page.config.clear_field_by_keys(params['field_name'])
        host_page.config.check_field_is_required(params['field_name'])
        host_page.config.type_in_field_with_few_inputs(
            row=host_page.config.get_all_config_rows()[0], values=[params['new_value']]
        )
        host_page.config.save_config()
        host_page.config.assert_input_value_is(expected_value=params["new_value"], display_name=params["field_name"])

    @pytest.mark.parametrize('provider_bundle', ["host_with_all_config_params"], indirect=True)
    @pytest.mark.usefixtures('create_host')
    def test_field_tooltips_on_host_config_page(self, page: HostListPage):
        """Test config fields tooltips on host config page"""

        host_page = open_config(page)
        for item in CONFIG_ITEMS:
            host_page.config.check_text_in_tooltip(item, f"Test description {item}")


@pytest.mark.usefixtures('_login_to_adcm_over_api')
class TestHostStatusPage:
    """Tests for the /host/{}/status page"""

    def test_open_by_tab_host_status_page(self, app_fs, create_host):
        """Test open /host/{}/config from left menu"""

        host_main_page = HostMainPage(app_fs.driver, app_fs.adcm.url, create_host.id).open()
        host_status_page = host_main_page.open_status_tab()
        host_status_page.check_all_elements()
        host_status_page.check_host_toolbar(HOST_FQDN)

    def test_status_on_host_status_page(self, app_fs, adcm_fs, sdk_client_fs, create_host, upload_and_create_cluster):
        """Changes status on cluster/{}/status page"""

        success_status = [
            StatusRowInfo(
                icon_status=True, group_name='best-host', state='successful 1/1', state_color=SUCCESS_COLOR, link=None
            ),
            StatusRowInfo(icon_status=True, group_name=None, state=None, state_color=None, link='first'),
        ]
        negative_status_component = [
            StatusRowInfo(
                icon_status=True, group_name='best-host', state='successful 0/1', state_color=NEGATIVE_COLOR, link=None
            ),
            StatusRowInfo(icon_status=False, group_name=None, state=None, state_color=None, link='first'),
        ]
        negative_status_host = [
            StatusRowInfo(
                icon_status=False, group_name='best-host', state='successful 0/1', state_color=NEGATIVE_COLOR, link=None
            ),
            StatusRowInfo(icon_status=False, group_name=None, state=None, state_color=None, link='first'),
        ]

        with allure.step("Create hostcomponent"):
            _, cluster = upload_and_create_cluster
            cluster.host_add(create_host)
            service = cluster.service_add(name="test_service")
            cluster.hostcomponent_set((create_host, service.component(name="first")))

        host_status_page = HostStatusPage(app_fs.driver, app_fs.adcm.url, create_host.id).open()
        status_changer = ADCMObjectStatusChanger(sdk_client_fs, adcm_fs)
        with allure.step("Check positive status"):
            status_changer.enable_cluster(cluster)
            host_status_page.driver.refresh()
            host_status_page.compare_current_and_expected_state(success_status)
        with allure.step("Check negative status on component"):
            status_changer.set_component_negative_status(
                (create_host, cluster.service(name="test_service").component(name="first"))
            )
            host_status_page.driver.refresh()
            host_status_page.compare_current_and_expected_state(negative_status_component)
        with allure.step("Check negative status on host"):
            status_changer.set_host_negative_status(create_host)
            host_status_page.driver.refresh()
            host_status_page.compare_current_and_expected_state(negative_status_host)
        with allure.step("Check collapse button"):
            with host_status_page.wait_rows_collapsed():
                host_status_page.click_collapse_all_btn()
            assert len(host_status_page.get_all_rows()) == 1, "Status rows should have been collapsed"


class TestHostRenaming:

    SPECIAL_CHARS = (".", "-", "_")
    DISALLOWED_AT_START = (".", "-")
    EXPECTED_ERROR = "Please enter a valid name"

    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_rename_host(self, sdk_client_fs, app_fs, create_host):
        host = create_host
        page = HostListPage(app_fs.driver, app_fs.adcm.url).open()
        self._test_correct_name_can_be_set(host, page)
        self._test_an_error_is_shown_on_incorrect_char_in_name(page)
        self._test_an_error_is_not_shown_on_correct_char_in_name(page)

    @allure.step("Check settings new correct host FQDN")
    def _test_correct_name_can_be_set(self, host: Host, page: HostListPage) -> None:
        new_name = "best-host.fqdn"

        dialog = page.open_rename_dialog(page.get_host_row())
        dialog.set_new_name_in_rename_dialog(new_name)
        dialog.click_save_on_rename_dialog()
        with allure.step("Check fqdn of host in table"):
            name_in_row = page.get_host_info_from_row(0).fqdn
            assert name_in_row == new_name, f"Incorrect cluster name, expected: {new_name}"
            host.reread()
            assert host.fqdn == new_name, f"Host FQDN on backend is incorrect, expected: {new_name}"

    def _test_an_error_is_shown_on_incorrect_char_in_name(self, page: HostListPage) -> None:
        dummy_name = "hOst"
        incorrect_names = (
            *[f"{char}{dummy_name}" for char in self.DISALLOWED_AT_START],
            *[f"{dummy_name[0]}{char}{dummy_name[1:]}" for char in ("и", "!", " ")],
        )

        dialog = page.open_rename_dialog(page.get_host_row())

        for fqdn in incorrect_names:
            with allure.step(f"Check if printing host FQDN '{fqdn}' triggers a warning message"):
                dialog.set_new_name_in_rename_dialog(dummy_name)
                dialog.set_new_name_in_rename_dialog(fqdn)
                assert dialog.is_dialog_error_message_visible(), "Error about incorrect name should be visible"
                assert (
                    dialog.get_dialog_error_message() == self.EXPECTED_ERROR
                ), f"Incorrect error message, expected: {self.EXPECTED_ERROR}"

        dialog.click_cancel_on_rename_dialog()

    def _test_an_error_is_not_shown_on_correct_char_in_name(self, page: HostListPage) -> None:
        dummy_name = "clUster"
        correct_names = (
            *[f"{dummy_name[0]}{char}{dummy_name[1:]}" for char in (".", "-", "9")],
            f"9{dummy_name}",
            f"{dummy_name}-",
        )

        dialog = page.open_rename_dialog(page.get_host_row())

        for fqdn in correct_names:
            with allure.step(f"Check if printing host FQDN '{fqdn}' shows no error"):
                dialog.set_new_name_in_rename_dialog(dummy_name)
                dialog.set_new_name_in_rename_dialog(fqdn)
                assert not dialog.is_dialog_error_message_visible(), "Error about correct name should not be shown"
                dialog.click_save_on_rename_dialog()
                name_in_row = page.get_host_info_from_row().fqdn
                assert name_in_row == fqdn, f"Incorrect host FQDN, expected: {fqdn}"
                dialog = page.open_rename_dialog(page.get_host_row())
