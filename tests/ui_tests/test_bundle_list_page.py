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
from typing import List

import os
import yaml
import pytest
import allure
import tarfile

from _pytest.fixtures import SubRequest
from pathlib import PosixPath
from adcm_pytest_plugin import utils
from adcm_client.objects import ADCMClient, Bundle

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin_intro.page import AdminIntroPage
from tests.ui_tests.app.page.bundle.page import BundlePage
from tests.ui_tests.app.page.bundle_list.locators import BundleListLocators
from tests.ui_tests.app.page.bundle_list.page import BundleListPage, BundleInfo
from tests.ui_tests.app.page.host_list.page import HostListPage
from tests.ui_tests.utils import check_rows_amount


def _assert_bundle_info_value(attribute: str, actual_info: BundleInfo, expected_info: BundleInfo):
    actual_value = getattr(actual_info, attribute)
    expected_value = getattr(expected_info, attribute)
    assert (
        actual_value == expected_value
    ), f"Bundle's {attribute} should be {expected_value}, not {actual_value}"


@allure.step('Check bundle info')
def check_bundle_info_is_equal(actual_info: BundleInfo, expected_info: BundleInfo):
    for attr in ('name', 'description', 'version', 'edition'):
        _assert_bundle_info_value(attr, actual_info, expected_info)


# pylint: disable=redefined-outer-name
@pytest.fixture()
def page(app_fs: ADCMTest, login_to_adcm_over_api) -> BundleListPage:
    """Get BundleListPage after authorization"""
    return BundleListPage(app_fs.driver, app_fs.adcm.url).open()


@pytest.fixture(params=["cluster_community"])
@allure.title("Upload bundle")
def upload_bundle(request: SubRequest, sdk_client_fs: ADCMClient) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), request.param))


@pytest.fixture()
def _create_connected_objects(upload_bundle: Bundle):
    """Upload bundle and create cluster"""
    upload_bundle.cluster_create('Best Cluster Ever')


@pytest.fixture(params=[12])
def spam_bundles(request, tmp_path: PosixPath) -> List[str]:
    """
    Create dummy bundle archives to test pagination
    :returns: list with paths to archives
    """
    archives = []
    for i in range(request.param):
        archive_path = tmp_path / f'spam_bundle_{i}.tar'
        config_fp = (bundle_dir := tmp_path / f'spam_bundle_{i}') / 'config.yaml'
        bundle_dir.mkdir()
        config = [
            {
                'type': 'cluster',
                'name': f'spam_cluster_{i}',
                'version': str(i),
            }
        ]
        with open(config_fp, 'w') as config_file:
            yaml.safe_dump(config, config_file)
        with tarfile.open(archive_path, 'w') as archive:
            archive.add(config_fp, arcname='config.yaml')
        archives.append(str(archive_path))
    return archives


@pytest.fixture()
def _upload_spam_bundles(sdk_client_fs: ADCMClient, spam_bundles: List[str]):
    """Upload spam bundles"""
    for bundle in spam_bundles:
        sdk_client_fs.upload_from_fs(bundle)


@pytest.mark.parametrize(
    "bundle_archive",
    [pytest.param(utils.get_data_dir(__file__, "cluster_community"), id="community")],
    indirect=True,
)
def test_ce_bundle_upload(bundle_archive: str, page: BundleListPage):
    """Upload community bundle"""
    bundle_params = BundleInfo(
        name="test_cluster", version="1.5", edition="community", description="community description"
    )
    page.upload_bundle(bundle_archive)
    bundle_info = page.get_bundle_info()
    check_bundle_info_is_equal(bundle_info, bundle_params)


@pytest.mark.parametrize(
    "bundle_archive",
    [pytest.param(utils.get_data_dir(__file__, "cluster_enterprise"), id="enterprise")],
    indirect=True,
)
def test_ee_bundle_upload(bundle_archive: str, page: BundleListPage):
    """Upload enterprise bundle and accept licence"""
    bundle_params = BundleInfo(
        name="test_cluster",
        version="1.5",
        edition="enterprise",
        description="enterprise description",
    )
    page.upload_bundle(bundle_archive)
    page.accept_licence()
    bundle_info = page.get_bundle_info()
    check_bundle_info_is_equal(bundle_info, bundle_params)


@pytest.mark.parametrize(
    "bundle_archive",
    [pytest.param(utils.get_data_dir(__file__, "cluster_enterprise"), id="enterprise")],
    indirect=True,
)
def test_delete_bundle(bundle_archive: str, page: BundleListPage):
    """Upload bundle and delete it"""
    with allure.step('Upload bundle'):
        page.upload_bundle(bundle_archive)
        assert page.table.row_count == 1, 'One bundle should be uploaded'
    with allure.step('Delete bundle'):
        page.delete_bundle()
        assert page.table.row_count == 0, 'No bundle should be listed in the table'


@pytest.mark.full()
@pytest.mark.parametrize(
    "bundle_archives",
    [
        pytest.param(
            (
                utils.get_data_dir(__file__, "cluster_community"),
                utils.get_data_dir(__file__, "cluster_enterprise"),
            )
        ),
    ],
    indirect=True,
)
def test_two_bundles(bundle_archives: List[str], page: BundleListPage):
    """Upload two bundles"""
    with page.table.wait_rows_change():
        page.upload_bundle(bundle_archives[0])
    with page.table.wait_rows_change():
        page.upload_bundle(bundle_archives[1])
    with allure.step('Check amount of rows'):
        rows = page.table.row_count
        assert rows == 2, f'Row amount should be 2, but only {rows} is presented'


def test_open_bundle_from_table(page: BundleListPage, upload_bundle: Bundle):
    """Test open bundle object page from list of bundles"""
    with allure.step('Open bundle object page from bundle list'):
        page.click_bundle_in_row()
    with allure.step('Check object page is opened'):
        object_page = BundlePage(page.driver, page.base_url, upload_bundle.id)
        object_page.wait_page_is_opened()


def test_open_main_menu_on_bundle_page(page: BundleListPage, upload_bundle: Bundle):
    with allure.step('Open bundle object page'):
        object_page = BundlePage(page.driver, page.base_url, upload_bundle.id)
        object_page.open()
    object_page.open_main_menu()
    object_page.check_all_fields_presented()


@pytest.mark.full()
@pytest.mark.usefixtures('upload_bundle')
def test_open_adcm_main_menu(page: BundleListPage):
    """Open main menu by clicking on the menu icon in toolbar"""
    page.find_and_click(BundleListLocators.Tooltip.apps_btn)
    AdminIntroPage(page.driver, page.base_url).wait_page_is_opened()


@pytest.mark.full()
@pytest.mark.usefixtures("_create_connected_objects")
def test_delete_provider_with_created_cluster(page: BundleListPage):
    """
    Bundle should not be deleted if an object defined in it is created
    """
    page.delete_bundle()
    with allure.step('Check bundle is visible'):
        page.check_element_should_be_visible(BundleListLocators.Table.row)


@pytest.mark.parametrize(
    "bundle_archive",
    [utils.get_data_dir(__file__, "provider")],
    indirect=True,
    ids=['provider_bundle'],
)
def test_create_bundle_from_another_page(
    page: BundleListPage, app_fs: ADCMTest, bundle_archive: str
):
    """
    Upload bundle from host list and check it is presented in table
    """
    expected_info = BundleInfo(
        name='test_provider', version='2.15-dev', edition='community', description=''
    )
    with allure.step('Check bundle list is empty'):
        assert (
            row_count := page.table.row_count
        ) == 0, f'Bundle list should be empty, but {row_count} records was found'
    with allure.step('Create bundle from host creation popup'):
        host_list_page = HostListPage(app_fs.driver, app_fs.adcm.url).open()
        host_list_page.upload_bundle(bundle_archive)
    with allure.step('Check bundle is listed in table'):
        page.open()
        assert (
            row_count := page.table.row_count
        ) == 1, f'Bundle list should has exactly 1 record, but {row_count} was found'
        bundle_info = page.get_bundle_info()
        check_bundle_info_is_equal(bundle_info, expected_info)


@pytest.mark.usefixtures("_upload_spam_bundles")
def test_bundle_list_pagination(page: BundleListPage):
    """Upload 12 bundles and check pagination"""
    params = {'on_first_page': 10, 'on_second_page': 2}
    page.close_info_popup()
    with allure.step("Check pagination"):
        with page.table.wait_rows_change():
            page.table.click_page_by_number(2)
        check_rows_amount(page, params['on_second_page'], 2)
        with page.table.wait_rows_change():
            page.table.click_previous_page()
        check_rows_amount(page, params['on_first_page'], 1)
        with page.table.wait_rows_change():
            page.table.click_next_page()
        check_rows_amount(page, params['on_second_page'], 2)
        with page.table.wait_rows_change():
            page.table.click_page_by_number(1)
        check_rows_amount(page, params['on_first_page'], 1)
