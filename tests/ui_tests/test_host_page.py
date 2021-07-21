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
    "bundle_archive", [utils.get_data_dir(__file__, "provider")], indirect=True
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


def test_run_action_on_new_host():
    """Create host and run action on it"""


@pytest.mark.full
def test_open_config_from_host_list():
    """Create host and open configuration from host list"""


@pytest.mark.full
def test_open_status_from_host_list():
    """Create host and open status page from host list"""


def test_open_host_from_host_list():
    """Create host and open host page from host list"""


@pytest.mark.parametrize(
    "bundle_archive",
    [utils.get_data_dir(__file__, "provider")],
    indirect=True,
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


def test_run_action_from_menu():
    """Run action from host actions menu"""


@pytest.mark.full
def test_filter_config():
    """Use filters on host configuration page"""


def test_set_custom_name_in_config():
    """Change name in host configuration"""


@pytest.mark.full
def test_reset_configuration():
    """Change configuration, save, reset to defaults"""


@pytest.mark.full
def test_field_validation():
    """Inputs are validated correctly"""
