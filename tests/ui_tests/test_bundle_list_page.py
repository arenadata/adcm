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

"""UI tests for /bundle page"""

import os
from typing import List

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.utils import catch_failed
from selenium.common.exceptions import ElementClickInterceptedException
from tests.conftest import DUMMY_CLUSTER_BUNDLE
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.bundle.page import BundlePage
from tests.ui_tests.app.page.bundle_list.page import BundleInfo, BundleListPage
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.host_list.page import HostListPage

LICENSE_FP = os.path.join(utils.get_data_dir(__file__), 'license.txt')

CLUSTER_CE_CONFIG = DUMMY_CLUSTER_BUNDLE

CLUSTER_EE_CONFIG = [
    {
        **CLUSTER_CE_CONFIG[0],
        'description': 'enterprise description',
        'license': 'license.txt',
        'edition': 'enterprise',
    }
]

PROVIDER_CONFIG = [
    {
        'type': 'provider',
        'name': 'test_provider',
        'version': '2.15-dev',
    },
    {
        'type': 'host',
        'name': 'Test Host',
        'description': 'Test Host Description',
        'version': '2.15-dev',
    },
]


def _assert_bundle_info_value(attribute: str, actual_info: BundleInfo, expected_info: BundleInfo):
    actual_value = getattr(actual_info, attribute)
    expected_value = getattr(expected_info, attribute)
    assert actual_value == expected_value, f"Bundle's {attribute} should be {expected_value}, not {actual_value}"


# pylint: disable=redefined-outer-name
@allure.step('Check bundle list is empty')
def _check_bundle_list_is_empty(page: BundleListPage):
    assert (row_count := page.table.row_count) == 0, f'Bundle list should be empty, but {row_count} records was found'


@allure.step('Check bundle is listed in table')
def _open_bundle_list_and_check_info(page: BundleListPage, expected_info: BundleInfo):
    """
    Open bundle list page, check that exactly 1 row is presented and check it's info
    """
    page.open()
    assert (
        row_count := page.table.row_count
    ) == 1, f'Bundle list should have exactly 1 record, but {row_count} was found'
    bundle_info = page.get_bundle_info()
    check_bundle_info_is_equal(bundle_info, expected_info)


@allure.step('Check bundle info')
def check_bundle_info_is_equal(actual_info: BundleInfo, expected_info: BundleInfo):
    """Assert bundle attrs values"""
    for attr in ('name', 'description', 'version', 'edition'):
        _assert_bundle_info_value(attr, actual_info, expected_info)


@pytest.fixture()
# pylint: disable-next=unused-argument
def page(app_fs: ADCMTest, _login_to_adcm_over_api) -> BundleListPage:
    """Get BundleListPage after authorization"""
    return BundleListPage(app_fs.driver, app_fs.adcm.url).open()


@allure.title("Upload bundles")
@pytest.fixture()
def upload_bundles(create_bundle_archives: List[str], sdk_client_fs: ADCMClient) -> List[Bundle]:
    """Upload bundles to ADCM"""
    return [sdk_client_fs.upload_from_fs(path) for path in create_bundle_archives]


@pytest.fixture()
def _create_cluster(upload_bundles: List[Bundle]):
    """Upload bundles and create cluster from first bundle"""
    upload_bundles[0].cluster_create('Best Cluster Ever')


@pytest.mark.smoke()
@pytest.mark.include_firefox()
def test_ce_bundle_upload(create_bundle_archives: List[str], page: BundleListPage):
    """Upload community bundle"""
    bundle_params = BundleInfo(
        name="test_cluster", version="1.5", edition="community", description="community description"
    )
    page.upload_bundle(create_bundle_archives[0])
    bundle_info = page.get_bundle_info()
    check_bundle_info_is_equal(bundle_info, bundle_params)


@pytest.mark.smoke()
@pytest.mark.include_firefox()
@pytest.mark.parametrize("create_bundle_archives", [([CLUSTER_EE_CONFIG], LICENSE_FP)], indirect=True)
def test_ee_bundle_upload(create_bundle_archives: List[str], page: BundleListPage):
    """Upload enterprise bundle and accept licence"""
    bundle_params = BundleInfo(
        name='test_cluster',
        version='1.5',
        edition='enterprise',
        description='enterprise description',
    )
    page.upload_bundle(create_bundle_archives[0])
    page.accept_licence()
    bundle_info = page.get_bundle_info()
    check_bundle_info_is_equal(bundle_info, bundle_params)


@pytest.mark.smoke()
@pytest.mark.include_firefox()
def test_delete_bundle(create_bundle_archives: List[str], page: BundleListPage):
    """Upload bundle and delete it"""
    with allure.step('Upload bundle'):
        page.upload_bundle(create_bundle_archives[0])
        assert page.table.row_count == 1, 'One bundle should be uploaded'
    with allure.step('Delete bundle'):
        page.delete_bundle()
        assert page.table.row_count == 0, 'No bundle should be listed in the table'


@pytest.mark.parametrize(
    "create_bundle_archives", [([CLUSTER_CE_CONFIG, CLUSTER_EE_CONFIG], LICENSE_FP)], indirect=True
)
def test_two_bundles(create_bundle_archives: List[str], page: BundleListPage):
    """Upload two bundles"""
    with allure.step('Upload 1st bundle'), page.table.wait_rows_change():
        page.upload_bundle(create_bundle_archives[0])
    with allure.step('Upload 2nd bundle'), page.table.wait_rows_change():
        page.upload_bundle(create_bundle_archives[1])
    with allure.step('Check there are exactly 2 rows'):
        rows = page.table.row_count
        assert rows == 2, f'Row amount should be 2, but only {rows} is presented'


@allure.issue("https://arenadata.atlassian.net/browse/ADCM-2010")
@pytest.mark.skip(reason="Not worked using selenoid https://github.com/aerokube/selenoid/issues/844")
@pytest.mark.parametrize(
    "create_bundle_archives", [([CLUSTER_CE_CONFIG, CLUSTER_EE_CONFIG], LICENSE_FP)], indirect=True
)
def test_accept_license_with_two_bundles_upload_at_once(create_bundle_archives: List[str], page: BundleListPage):
    """Upload two bundles and accept license"""
    with page.table.wait_rows_change():
        page.upload_bundles(create_bundle_archives)
    with catch_failed(ElementClickInterceptedException, "License was not accepted by single button click"):
        page.accept_licence(row_num=1)


@pytest.mark.xfail(reason="https://arenadata.atlassian.net/browse/ADCM-2385")
@pytest.mark.smoke()
@pytest.mark.include_firefox()
def test_open_bundle_from_table(page: BundleListPage, upload_bundles: List[Bundle]):
    """Test open bundle object page from list of bundles"""
    with allure.step('Open bundle object page from bundle list'):
        page.click_bundle_in_row(page.table.get_row())
    with allure.step('Check object page is opened'):
        object_page = BundlePage(page.driver, page.base_url, upload_bundles[0].id)
        object_page.wait_page_is_opened()
        object_page.check_bundle_toolbar(CLUSTER_CE_CONFIG[0]["name"].upper())


@pytest.mark.xfail(reason="https://arenadata.atlassian.net/browse/ADCM-2385")
@pytest.mark.smoke()
@pytest.mark.include_firefox()
def test_open_main_menu_on_bundle_page(page: BundleListPage, upload_bundles: List[Bundle]):
    """Open main menu on bundle detailed page"""
    with allure.step('Open bundle object page'):
        object_page = BundlePage(page.driver, page.base_url, upload_bundles[0].id)
        object_page.open()
    object_page.open_main_menu()
    object_page.check_all_main_menu_fields_are_presented()
    object_page.check_bundle_toolbar(CLUSTER_CE_CONFIG[0]["name"].upper())


@pytest.mark.usefixtures('upload_bundles')
def test_open_adcm_main_menu(page: BundleListPage):
    """Open main menu by clicking on the menu icon in toolbar"""
    page.click_on_home_button_on_toolbar()
    AdminIntroPage(page.driver, page.base_url).wait_page_is_opened()


@pytest.mark.usefixtures("_create_cluster")
def test_delete_bundle_with_created_cluster(page: BundleListPage):
    """
    Bundle should not be deleted if an object defined in it is created
    """
    page.delete_bundle()
    page.check_at_least_one_bundle_is_presented()


@pytest.mark.smoke()
@pytest.mark.include_firefox()
@pytest.mark.parametrize(
    "create_bundle_archives",
    [[PROVIDER_CONFIG]],
    indirect=True,
    ids=['provider_bundle'],
)
def test_upload_provider_bundle_from_another_page(
    page: BundleListPage, app_fs: ADCMTest, create_bundle_archives: List[str]
):
    """
    Upload bundle from host list and check it is presented in table
    """
    expected_info = BundleInfo(name='test_provider', version='2.15-dev', edition='community', description='')
    _check_bundle_list_is_empty(page)
    with allure.step('Create bundle from host creation popup'):
        host_list_page = HostListPage(app_fs.driver, app_fs.adcm.url).open()
        host_list_page.upload_bundle_from_host_create_popup(create_bundle_archives[0])
    _open_bundle_list_and_check_info(page, expected_info)


@pytest.mark.smoke()
@pytest.mark.include_firefox()
@pytest.mark.parametrize(
    "create_bundle_archives",
    [[CLUSTER_CE_CONFIG]],
    indirect=True,
    ids=['cluster_bundle'],
)
def test_upload_cluster_bundle_from_another_page(
    page: BundleListPage, app_fs: ADCMTest, create_bundle_archives: List[str]
):
    """Upload bundle from cluster list and check it is presented in table"""
    expected_info = BundleInfo(
        name='test_cluster', version='1.5', edition='community', description='community description'
    )
    _check_bundle_list_is_empty(page)
    with allure.step('Create bundle from cluster creation popup'):
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.upload_bundle_from_cluster_create_popup(create_bundle_archives[0])
    _open_bundle_list_and_check_info(page, expected_info)


@pytest.mark.parametrize(
    "create_bundle_archives",
    [[[{'type': 'cluster', 'name': f'ihavetodance-{i}', 'version': f'{i}-ver'}] for i in range(12)]],
    indirect=True,
)
@pytest.mark.usefixtures("upload_bundles")
def test_bundle_list_pagination(page: BundleListPage):
    """Upload 12 bundles and check pagination"""
    params = {'on_first_page': 10, 'on_second_page': 2}
    page.close_info_popup()
    page.table.check_pagination(params['on_second_page'])
