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
from typing import Any, List, Tuple, Optional

import os
import allure
import pytest
from _pytest.fixtures import SubRequest

from adcm_client.objects import ADCMClient, Bundle, Provider, Cluster
from adcm_pytest_plugin import utils

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.admin_intro.page import AdminIntroPage
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.host.locators import HostLocators
from tests.ui_tests.app.page.host.page import HostPage
from tests.ui_tests.app.page.host_list.locators import HostListLocators
from tests.ui_tests.app.page.host_list.page import HostListPage, HostRowInfo

# pylint: disable=W0621


# defaults
HOST_FQDN = 'best-host'
CLUSTER_NAME = 'Best Cluster Ever'
PROVIDER_NAME = 'Black Mark'

# config fields
REGULAR_FIELD_ADCM_TEST = 'item_1_g1/item_1_g1'
REQUIRED_FIELD_ADCM_TEST = 'item_2_g1/item_2_g1'
PASSWORD_FIELD_ADCM_TEST = 'important_password'
ADVANCED_FIELD_ADCM_TEST = 'advanced_one'


@pytest.fixture(params=["provider"])
@allure.title("Upload provider bundle")
def provider_bundle(request: SubRequest, sdk_client_fs: ADCMClient) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), request.param))


@pytest.fixture()
@allure.title("Create provider")
def upload_and_create_provider(provider_bundle) -> Tuple[Bundle, Provider]:
    provider = provider_bundle.provider_create(PROVIDER_NAME)
    return provider_bundle, provider


@pytest.fixture()
@allure.title("Create host")
def _create_host(upload_and_create_provider: Tuple[Bundle, Provider]):
    """Create default host using API"""
    provider = upload_and_create_provider[1]
    provider.host_create(HOST_FQDN)


@pytest.fixture()
@allure.title("Create many hosts")
def _create_many_hosts(request, upload_and_create_provider):
    """Pass amount in param"""
    provider = upload_and_create_provider[1]
    for i in range(request.param):
        provider.host_create(f'no-fantasy-{i}')


@pytest.fixture()
@allure.title("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), "cluster"))


@pytest.fixture()
@allure.title("Create cluster")
def upload_and_create_cluster(cluster_bundle: Bundle) -> Tuple[Bundle, Cluster]:
    cluster = cluster_bundle.cluster_prototype().cluster_create(CLUSTER_NAME)
    return cluster_bundle, cluster


@pytest.fixture()
def page(app_fs: ADCMTest, auth_to_adcm) -> HostListPage:
    return HostListPage(app_fs.driver, app_fs.adcm.url).open()


@allure.step("Check elements aren't visible")
def elements_should_be_hidden(page: BasePageObject, locators: List[Locator]):
    # should be faster than alternatives to not is_visible and stuff
    for loc in locators:
        page.element_should_be_hidden(loc)


@allure.step('Open host config menu from host list')
def open_config(page) -> HostPage:
    page.click_on_row_child(0, HostListLocators.HostTable.HostRow.config)
    return HostPage(page.driver, page.base_url)


def check_host_value(key: str, actual_value: Any, expected_value: Any):
    """
    Assert that actual value equals to expected value
    Argument `key` is used in failed assertion message
    """
    assert (
        actual_value == expected_value
    ), f"Host {key} should be {expected_value}, not {actual_value}"


def check_host_info(
    host_info: HostRowInfo, fqdn: str, provider: str, cluster: Optional[str], state: str
):
    """Check all values in host info"""
    check_host_value('FQDN', host_info.fqdn, fqdn)
    check_host_value('provider', host_info.provider, provider)
    check_host_value('cluster', host_info.cluster, cluster)
    check_host_value('state', host_info.state, state)


def check_rows_amount(page, expected_amount: int, page_num: int):
    """Check rows count is equal to expected"""
    assert (
        page.table.row_count == expected_amount
    ), f'Page #{page_num}  should contain {expected_amount}'


def _check_menu(
    menu_name: str,
    provider_bundle: Bundle,
    list_page: HostListPage,
):
    list_page.click_on_row_child(0, HostListLocators.HostTable.HostRow.fqdn)
    host_page = HostPage(list_page.driver, list_page.base_url)
    getattr(host_page, f'open_{menu_name}_menu')()
    host_page.assert_fqdn_is(HOST_FQDN)
    bundle_label = host_page.get_bundle_label()
    # Test Host is name of host in config.yaml
    assert 'Test Host' in bundle_label
    assert provider_bundle.version in bundle_label


# !===== TESTS =====!


@pytest.mark.parametrize(
    "bundle_archive",
    [utils.get_data_dir(__file__, "provider")],
    indirect=True,
    ids=['provider_bundle'],
)
def test_create_host_with_bundle_upload(page: HostListPage, bundle_archive: str):
    """Upload bundle and create host"""
    host_fqdn = 'howdy-host-fqdn'
    new_provider_name = page.create_provider_and_host(bundle_archive, host_fqdn)
    host_info = page.get_host_info_from_row(0)
    check_host_info(host_info, host_fqdn, new_provider_name, None, 'created')


def test_create_bonded_to_cluster_host(
    page: HostListPage,
    upload_and_create_provider: Tuple[Bundle, Provider],
    upload_and_create_cluster: Tuple[Bundle, Provider],
):
    """Create host bonded to cluster"""
    host_fqdn = 'cluster-host'
    page.create_host(host_fqdn, cluster=CLUSTER_NAME)
    host_info = page.get_host_info_from_row(0)
    check_host_info(host_info, host_fqdn, PROVIDER_NAME, CLUSTER_NAME, 'created')


@pytest.mark.full()
@pytest.mark.parametrize("_create_many_hosts", [12], indirect=True)
@pytest.mark.usefixtures("_create_many_hosts")
def test_host_list_pagination(page: HostListPage):
    """Create more than 10 hosts and check pagination"""
    hosts_on_first_page, hosts_on_second_page = 10, 2
    page.close_info_popup()
    with allure.step("Check pagination"):
        with page.table.wait_rows_change():
            page.table.click_page_by_number(2)
        check_rows_amount(page, hosts_on_second_page, 2)
        with page.table.wait_rows_change():
            page.table.click_previous_page()
        check_rows_amount(page, hosts_on_first_page, 1)
        with page.table.wait_rows_change():
            page.table.click_next_page()
        check_rows_amount(page, hosts_on_second_page, 2)
        with page.table.wait_rows_change():
            page.table.click_page_by_number(1)
        check_rows_amount(page, hosts_on_first_page, 1)


def test_bind_host_to_cluster(
    page: HostListPage,
    upload_and_create_provider: Tuple[Bundle, Provider],
    upload_and_create_cluster: Tuple[Bundle, Provider],
):
    """Create host and go to cluster from host list"""
    page.create_host(HOST_FQDN)
    with allure.step("Check host created and isn't bound to a cluster"):
        host_info = page.get_host_info_from_row(0)
        check_host_info(host_info, HOST_FQDN, PROVIDER_NAME, None, 'created')
    page.bind_host_to_cluster(0, CLUSTER_NAME)
    page.assert_host_bonded_to_cluster(0, CLUSTER_NAME)


@pytest.mark.parametrize(
    ('row_child_name', 'menu_item_name'),
    [
        pytest.param('fqdn', 'main', id='open_host_main'),
        pytest.param('status', 'status', id='open_status_menu', marks=pytest.mark.full),
        pytest.param('config', 'config', id='open_config_menu', marks=pytest.mark.full),
    ],
)
@pytest.mark.usefixtures('_create_host')
def test_open_host_from_host_list(
    page: HostListPage,
    row_child_name: str,
    menu_item_name: str,
):
    """Test open host page from host list"""
    row_child = getattr(HostListLocators.HostTable.HostRow, row_child_name)
    menu_item_locator = getattr(HostLocators.MenuNavigation, menu_item_name)
    page.click_on_row_child(0, row_child)
    main_host_page = HostPage(page.driver, page.base_url)
    with allure.step('Check correct menu is opened'):
        main_host_page.assert_fqdn_is(HOST_FQDN)
        assert main_host_page.active_menu_is(menu_item_locator)


@pytest.mark.usefixtures("_create_host")
def test_delete_host(
    sdk_client_fs: ADCMClient,
    page: HostListPage,
    upload_and_create_provider: Tuple[Bundle, Provider],
):
    """Create host and delete it"""
    host_info = page.get_host_info_from_row(0)
    check_host_info(host_info, HOST_FQDN, PROVIDER_NAME, None, 'created')
    page.delete_host(0)
    page.element_should_be_hidden(HostListLocators.HostTable.row)


def test_delete_bonded_host(
    sdk_client_fs: ADCMClient,
    page: HostListPage,
    upload_and_create_provider: Tuple[Bundle, Provider],
    upload_and_create_cluster: Tuple[Bundle, Provider],
):
    """Host shouldn't be deleted"""
    page.create_host(HOST_FQDN, cluster=CLUSTER_NAME)
    page.delete_host(0)
    page.element_should_be_visible(HostListLocators.HostTable.row)


@pytest.mark.full()
@pytest.mark.parametrize('menu', ['main', 'config', 'status', 'action'])
@pytest.mark.usefixtures('_create_host')
def test_open_menu(
    upload_and_create_provider: Tuple[Bundle, Provider],
    upload_and_create_cluster,
    page: HostListPage,
    menu: str,
):
    """Open main page and open menu from side navigation"""
    _check_menu(menu, upload_and_create_provider[0], page)


@pytest.mark.usefixtures('_create_host')
def test_run_action_on_new_host(
    page: HostListPage,
):
    """Create host and run action on it"""
    page.assert_host_state(0, 'created')
    page.run_action(0, 'Init')
    page.assert_host_state(0, 'running')


@pytest.mark.usefixtures('_create_host')
def test_run_action_from_menu(
    page: HostListPage,
):
    """Run action from host actions menu"""
    page.click_on_row_child(0, HostListLocators.HostTable.HostRow.fqdn)
    host_main_page = HostPage(page.driver, page.base_url)
    host_main_page.open_action_menu()
    action_name = 'Init'
    actions_before = host_main_page.get_action_names()
    assert action_name in actions_before, f'Action {action_name} should be listed in Actions menu'
    with allure.step('Run action "Init" from host Actions menu'):
        host_main_page.run_action_from_menu(action_name, open_menu=False)
        host_main_page.wait_element_hide(HostLocators.Actions.action_btn(action_name))
        host_main_page.wait_element_clickable(HostLocators.Actions.action_run_btn, timeout=10)
    actions_after = host_main_page.get_action_names(open_menu=False)
    with allure.step('Assert available actions set changed'):
        assert actions_before != actions_after, 'Action set did not change after "Init" action'


@pytest.mark.full()
@pytest.mark.parametrize('provider_bundle', ["provider_config"], indirect=True)
@pytest.mark.usefixtures('_create_host')
def test_filter_config(
    page: HostListPage,
):
    """Use filters on host configuration page"""
    host_page = open_config(page)
    field_input = CommonConfigMenu.field_input
    not_required_option = field_input(REGULAR_FIELD_ADCM_TEST)
    required_option = field_input(REQUIRED_FIELD_ADCM_TEST)
    password_fields = CommonConfigMenu.password_inputs(PASSWORD_FIELD_ADCM_TEST)
    advanced_option = field_input(ADVANCED_FIELD_ADCM_TEST)
    with allure.step('Check unfiltered configuration'):
        host_page.assert_displayed_elements([not_required_option, required_option, password_fields])
        assert not host_page.is_element_displayed(
            advanced_option
        ), 'Advanced option should not be visible'
    with allure.step('Check group roll up'):
        host_page.config.click_on_group('group_one')
        elements_should_be_hidden(host_page, [not_required_option, required_option])
        host_page.is_element_displayed(password_fields)
        host_page.config.click_on_group('group_one')
        host_page.element_should_be_visible(not_required_option)
    with allure.step('Check configuration with "Advanced" turned on'):
        host_page.find_and_click(CommonConfigMenu.advanced_label)
        host_page.element_should_be_visible(advanced_option)
        host_page.assert_displayed_elements([not_required_option, required_option, password_fields])
    with allure.step('Check search filtration'):
        host_page.config.search('Adv')
        host_page.is_element_displayed(advanced_option)
        elements_should_be_hidden(
            host_page, [not_required_option, required_option, password_fields]
        )
        host_page.find_and_click(CommonConfigMenu.advanced_label)
        host_page.element_should_be_hidden(advanced_option)


@pytest.mark.parametrize('provider_bundle', ["provider_config"], indirect=True)
@pytest.mark.usefixtures('_create_host')
def test_custom_name_config(
    page: HostListPage,
):
    """Change configuration, save with custom name, compare changes"""
    host_page = open_config(page)
    with allure.step('Change config description'):
        new_config_desc = 'my own config description'
        init_config_desc = host_page.config.set_description(new_config_desc)
    with allure.step('Change config values'):
        host_page.config.type_in_config_field('12', REQUIRED_FIELD_ADCM_TEST)
        host_page.config.fill_password_and_confirm_fields(
            'awesomepass', 'awesomepass', adcm_test=PASSWORD_FIELD_ADCM_TEST
        )
        host_page.config.save_config()
    with allure.step('Compare configurations'):
        host_page.config.compare_current_to(init_config_desc)
        host_page.config.config_diff_is_presented('', REQUIRED_FIELD_ADCM_TEST)
        host_page.config.config_diff_is_presented('***', PASSWORD_FIELD_ADCM_TEST)


@pytest.mark.full()
@pytest.mark.parametrize('provider_bundle', ["provider_config"], indirect=True)
@pytest.mark.usefixtures('_create_host')
def test_reset_configuration(
    page: HostListPage,
):
    """Change configuration, save, reset to defaults"""
    password_adcm_test, field_adcm_test = PASSWORD_FIELD_ADCM_TEST, REQUIRED_FIELD_ADCM_TEST
    host_page = open_config(page)
    host_page.config.fill_password_and_confirm_fields('pass', 'pass', adcm_test=password_adcm_test)
    host_page.config.type_in_config_field('42', adcm_test=field_adcm_test, clear=True)
    host_page.config.save_config()
    host_page.config.reset_to_default(field_adcm_test)
    host_page.config.reset_to_default(password_adcm_test)
    field_value = host_page.config.get_input_value(field_adcm_test)
    password_value = host_page.config.get_input_value(password_adcm_test, is_password=True)
    assert field_value == '', 'Value in Required field should be empty after reset'
    assert password_value == '', 'Value in Password field should be empty after reset'


@pytest.mark.full()
@pytest.mark.parametrize('provider_bundle', ["provider_config"], indirect=True)
@pytest.mark.usefixtures('_create_host')
def test_field_validation(
    page: HostListPage,
):
    """Inputs are validated correctly"""
    host_page = open_config(page)
    host_page.wait_element_visible(host_page.config.config.field_input(REGULAR_FIELD_ADCM_TEST))
    host_page.config.check_password_confirm_required('Important password')
    host_page.config.check_field_is_required('Required item')
    host_page.config.type_in_config_field('etonechislo', REGULAR_FIELD_ADCM_TEST)
    host_page.config.check_field_is_invalid('Just item')


@pytest.mark.full()
@pytest.mark.usefixtures('_create_host')
def test_open_adcm_main_menu(page: HostListPage):
    """Open main menu by clicking on the menu icon in toolbar"""
    page.find_and_click(HostListLocators.Tooltip.apps_btn)
    AdminIntroPage(page.driver, page.base_url).wait_url_contains_path("/admin/intro")
