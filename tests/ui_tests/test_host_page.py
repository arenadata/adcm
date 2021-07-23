"""
Smoke tests for /host
"""
from typing import Any, List, Tuple, Optional

import os
import allure
import pytest

from adcm_client.objects import ADCMClient, Bundle, Provider, Cluster
from adcm_pytest_plugin import utils

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.host.locators import HostLocators
from tests.ui_tests.app.page.host.page import HostPage
from tests.ui_tests.app.page.host_list.locators import HostListLocators
from tests.ui_tests.app.page.host_list.page import HostListPage, HostRowInfo


@allure.step("Upload provider bundle")
def provider_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), data_dir_name))


@allure.step("Create provider")
def upload_and_create_provider(
    sdk_client_fs: ADCMClient, data_dir_name: str, provider_name: str
) -> Tuple[Bundle, Provider]:
    bundle = provider_bundle(sdk_client_fs, data_dir_name)
    provider = bundle.provider_create(provider_name)
    return bundle, provider


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), data_dir_name))


@allure.step("Create cluster")
def upload_and_create_cluster(
    sdk_client_fs: ADCMClient, data_dir_name: str, cluster_name: str
) -> Tuple[Bundle, Cluster]:
    bundle = cluster_bundle(sdk_client_fs, data_dir_name)
    cluster = bundle.cluster_prototype().cluster_create(cluster_name)
    return bundle, cluster


@pytest.fixture()
def page(app_fs: ADCMTest, auth_to_adcm) -> HostListPage:
    return HostListPage(app_fs.driver, app_fs.adcm.url).open()


def check_host_value(key: str, actual_value: Any, expected_value: Any):
    """
    Assert that actual value equals to expected value
    Argument `key` is used in failed assertion message
    """
    assert (
        actual_value == expected_value,
        f"Host {key} should be {expected_value}, not {actual_value}",
    )


def check_host_info(
    host_info: HostRowInfo, fqdn: str, provider: str, cluster: Optional[str], state: str
):
    """Check all values in host info"""
    check_host_value('FQDN', host_info.fqdn, fqdn)
    check_host_value('provider', host_info.provider, provider)
    check_host_value('cluster', host_info.cluster, cluster)
    check_host_value('state', host_info.state, state)


def _check_menu(
    menu_name: str,
    list_page: HostListPage,
    app_fs: ADCMTest,
    sdk_client_fs: ADCMClient,
    bundle_archive: str,
):
    host_fqdn, provider_name = 'menu-host', 'Most Wanted'
    bundle, provider = upload_and_create_provider(sdk_client_fs, bundle_archive, provider_name)
    list_page.create_host(host_fqdn)
    list_page.click_on_row_child(0, HostListLocators.HostTable.HostRow.fqdn)
    host_page = HostPage(list_page.driver, app_fs.adcm.url)
    getattr(host_page, f'open_{menu_name}_menu')()
    assert host_page.get_fqdn() == host_fqdn
    bundle_label = host_page.get_bundle_label()
    # Test Host is name of host in config.yaml
    assert 'Test Host' in bundle_label
    assert bundle.version in bundle_label


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


@pytest.mark.parametrize(
    "bundle_archives",
    [(utils.get_data_dir(__file__, "provider"), utils.get_data_dir(__file__, "cluster"))],
    indirect=True,
    ids=['provider_cluster_bundles'],
)
def test_create_bonded_to_cluster_host(
    sdk_client_fs: ADCMClient,
    page: HostListPage,
    bundle_archives: List[str],
):
    """Create host bonded to cluster"""
    host_fqdn, cluster_name, provider_name = 'cluster-host', 'Awesome Pechora', 'Black Mark'
    upload_and_create_provider(sdk_client_fs, bundle_archives[0], provider_name)
    upload_and_create_cluster(sdk_client_fs, bundle_archives[1], cluster_name)
    page.create_host(host_fqdn, cluster=cluster_name)
    host_info = page.get_host_info_from_row(0)
    check_host_info(host_info, host_fqdn, provider_name, cluster_name, 'created')


@pytest.mark.full
def test_host_list_pagination():
    """Create 10 hosts and check pagination"""


@pytest.mark.parametrize(
    "bundle_archives",
    [(utils.get_data_dir(__file__, "provider"), utils.get_data_dir(__file__, "cluster"))],
    indirect=True,
    ids=['provider_cluster_bundles'],
)
def test_open_cluster_from_host_list(
    sdk_client_fs: ADCMClient,
    page: HostListPage,
    bundle_archives: List[str],
):
    """Create host and go to cluster from host list"""
    host_fqdn, cluster_name, provider_name = 'open-cluster', 'Clean Install', 'Black Mark'
    upload_and_create_provider(sdk_client_fs, bundle_archives[0], provider_name)
    upload_and_create_cluster(sdk_client_fs, bundle_archives[1], cluster_name)
    page.create_host(host_fqdn)
    host_info = page.get_host_info_from_row(0)
    check_host_info(host_info, host_fqdn, provider_name, None, 'created')
    page.assign_host_to_cluster(0, cluster_name)
    host_info = page.get_host_info_from_row(0)
    check_host_info(host_info, host_fqdn, provider_name, cluster_name, 'created')


@pytest.mark.parametrize(
    "bundle_archive",
    [utils.get_data_dir(__file__, "provider")],
    indirect=True,
    ids=['provider_bundle'],
)
@pytest.mark.parametrize(
    'row_child_name, menu_item_name',
    [
        pytest.param('fqdn', 'main', id='Host main page from host list'),
        pytest.param('status', 'status', id='Status menu from host list', marks=pytest.mark.full),
        pytest.param('config', 'config', id='Config menu from host list', marks=pytest.mark.full),
    ],
)
def test_open_host_from_host_list(
    sdk_client_fs: ADCMClient,
    page: HostListPage,
    bundle_archive: str,
    row_child_name: str,
    menu_item_name: str,
):
    """Test open host page from host list"""
    host_fqdn, provider_name = 'openair', 'Single Singer'
    row_child = getattr(HostListLocators.HostTable.HostRow, row_child_name)
    menu_item_locator = getattr(HostLocators.MenuNavigation, menu_item_name)
    upload_and_create_provider(sdk_client_fs, bundle_archive, provider_name)
    page.create_host(host_fqdn)
    page.click_on_row_child(0, row_child)
    main_host_page = HostPage(page.driver, page.base_url)
    with allure.step('Check correct menu is opened'):
        assert (
            page_fqdn := main_host_page.get_fqdn()
        ) == host_fqdn, f'Expected FQDN is {host_fqdn}, but FQDN in menu is {page_fqdn}'
        assert main_host_page.active_menu_is(menu_item_locator)


@pytest.mark.parametrize(
    "bundle_archive",
    [utils.get_data_dir(__file__, "provider")],
    indirect=True,
    ids=['provider_bundle'],
)
def test_delete_host(
    sdk_client_fs: ADCMClient,
    page: HostListPage,
    bundle_archive: str,
):
    """Create host and delete it"""
    host_fqdn, provider_name = 'doomed-host', 'Stuff Handler'
    _, provider = upload_and_create_provider(sdk_client_fs, bundle_archive, provider_name)
    page.create_host(host_fqdn)
    host_info = page.get_host_info_from_row(0)
    check_host_info(host_info, host_fqdn, provider_name, None, 'created')
    page.delete_host(0)
    page.wait_element_hide(HostListLocators.HostTable.row)


@pytest.mark.full
@pytest.mark.parametrize(
    "bundle_archive",
    [utils.get_data_dir(__file__, "provider")],
    indirect=True,
    ids=['provider_bundle'],
)
@pytest.mark.parametrize('menu', ['main', 'config', 'status', 'action'])
def test_open_menu(
    app_fs,
    bundle_archive,
    sdk_client_fs: ADCMClient,
    page: HostListPage,
    menu: str,
):
    """Open main page and open menu from side navigation"""
    _check_menu(menu, page, app_fs, sdk_client_fs, bundle_archive)


@pytest.mark.parametrize(
    "bundle_archive",
    [utils.get_data_dir(__file__, "provider")],
    indirect=True,
    ids=['provider_bundle'],
)
def test_run_action_on_new_host(
    bundle_archive,
    sdk_client_fs: ADCMClient,
    page: HostListPage,
):
    """Create host and run action on it"""
    upload_and_create_provider(sdk_client_fs, bundle_archive, 'prov')
    page.create_host('fqdn')
    page.wait_for_host_state(0, 'created')
    page.run_action(0, 'Init')
    page.wait_for_host_state(0, 'running')


@pytest.mark.parametrize(
    "bundle_archive",
    [utils.get_data_dir(__file__, "provider")],
    indirect=True,
    ids=['provider_bundle'],
)
def test_run_action_from_menu(
    bundle_archive,
    sdk_client_fs: ADCMClient,
    page: HostListPage,
):
    """Run action from host actions menu"""
    upload_and_create_provider(sdk_client_fs, bundle_archive, 'prov')
    page.create_host('fqdn')
    page.click_on_row_child(0, HostListLocators.HostTable.HostRow.fqdn)
    host_main_page = HostPage(page.driver, page.base_url)
    actions_before = host_main_page.get_action_names()
    with allure.step('Run action "Init" from host Actions menu'):
        host_main_page.run_action_from_menu('Init', open_menu=False)
        host_main_page.wait_element_clickable(HostLocators.Actions.action_run_btn, timeout=10)
    actions_after = host_main_page.get_action_names(open_menu=False)
    with allure.step('Assert available actions set changed'):
        assert actions_before != actions_after, 'Action set did not change after "Init" action'


@pytest.mark.full
def test_filter_config():
    """Use filters on host configuration page"""


@pytest.mark.full
def test_reset_configuration():
    """Change configuration, save, reset to defaults"""


@pytest.mark.full
def test_field_validation():
    """Inputs are validated correctly"""
