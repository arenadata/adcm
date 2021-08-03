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

import pytest
import allure

from adcm_pytest_plugin import utils

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.bundle_list.page import BundleListPage, BundleInfo


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
    page.upload_bundle(bundle_archive)
    assert page.table.row_count == 1, 'One bundle should be uploaded'
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
    rows = page.table.row_count
    assert rows == 2, f'Row amount should be 2, but only {rows} is presented'
