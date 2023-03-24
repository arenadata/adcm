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

"""Test service with license"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, Cluster
from adcm_pytest_plugin.utils import get_data_dir, wait_until_step_succeeds

from tests.ui_tests.app.page.cluster.page import ClusterServicesPage
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.common.dialogs.service_license import ServiceLicenseModal

FIRST_LICENSE_TEXT = "first license for service"
SECOND_LICENSE_TEXT = "second license for another service"

UPDATE_CLUSTER_TEXT = "The cluster will be prepared for upgrade"

OLD_CLUSTER_SECOND_LICENSE = "second license from new cluster and old cluster. They are equal"
OLD_CLUSTER_THIRD_LICENSE = "third license from old cluster on service_3"

NEW_CLUSTER_FIRST_LICENSE = "first license from new cluster for service_1"
NEW_CLUSTER_THIRD_LICENSE = "third license from new cluster service_4"

LICENSE_ERROR = '[ CONFLICT ] LICENSE_ERROR -- License for prototype "service_4" service 2.0 is not accepted'


@pytest.fixture(name="service_license_cluster")
def bundle_with_first_license(sdk_client_fs: ADCMClient) -> Cluster:
    """Upload bundle with license"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "license1"))
    cluster = bundle.cluster_create(name="license_service")
    return cluster


@pytest.fixture(name="service_license_bundle_old")
def bundle_old(sdk_client_fs) -> Bundle:
    """Upload cluster without license service"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "old_cluster"))


@pytest.fixture(name="service_license_bundle_new")
def bundle_new(sdk_client_fs) -> Bundle:
    """Upload cluster with license service"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "new_cluster"))


@allure.step("Check that cluster has been upgraded")
def check_cluster_upgraded(app_fs, upgrade_cluster_name: str, state: str):
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    row = cluster_page.get_row_by_cluster_name(upgrade_cluster_name)
    assert cluster_page.get_cluster_state_from_row(row) == state, f"Cluster state should be {state}"


def add_service_and_get_license(page: ClusterServicesPage, service_name: str) -> ServiceLicenseModal:
    page.click_add_service_button()
    page.find_service(service_name=service_name).click()
    page.click_add_service_in_dialog()
    return page.get_service_license_dialog()


@pytest.mark.usefixtures("_login_to_adcm_over_api")
def test_service_license_no_update(app_fs, service_license_cluster):
    cluster = service_license_cluster
    cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()

    with allure.step("Check service license text, without accepting license"):
        license_dialog_window = add_service_and_get_license(page=cluster_service_page, service_name="service_1 - 1.0")
        license_text = license_dialog_window.get_text()
        license_dialog_window.reject_license()

        assert (
            license_text == FIRST_LICENSE_TEXT
        ), f"Wrong text of license, actual text: {license_text}\nexpected text: {FIRST_LICENSE_TEXT}"
        assert (
            len(cluster.service_list()) == 0
        ), f"If license is not accepted, list of services should be empty. Services: {len(cluster.service_list())}"

    with allure.step("Add service without license"):
        cluster_service_page.add_service_by_name(service_name="service_4 - 1.0")
        assert (
            len(cluster.service_list()) == 1
        ), f"Service without license should be added to cluster. Services: {len(cluster.service_list())}"

    with allure.step("Add two services with difference license"):
        license_dialog_window = add_service_and_get_license(page=cluster_service_page, service_name="service_1 - 1.0")
        license_dialog_window.accept_license()

        license_dialog_window = add_service_and_get_license(page=cluster_service_page, service_name="service_3 - 1.0")
        license_text = license_dialog_window.get_text()

        assert (
            license_text == SECOND_LICENSE_TEXT
        ), f"Wrong text of license, actual text: {license_text}\nexpected text: {SECOND_LICENSE_TEXT}"
        license_dialog_window.accept_license()

    with allure.step("Add service with license from first service"):
        license_dialog_window = add_service_and_get_license(page=cluster_service_page, service_name="service_2 - 1.0")
        license_dialog_window.accept_license()

    with allure.step("Delete service with license and add it again"):
        service_1 = cluster.service(name="service_1")
        cluster.service_delete(service_1)
        service_3 = cluster.service(name="service_3")
        cluster.service_delete(service_3)

        license_dialog_window = add_service_and_get_license(page=cluster_service_page, service_name="service_1 - 1.0")
        license_dialog_window.accept_license()
        license_dialog_window = add_service_and_get_license(page=cluster_service_page, service_name="service_3 - 1.0")
        license_dialog_window.accept_license()


@pytest.mark.usefixtures("_login_to_adcm_over_api")
def test_service_license_update(app_fs, service_license_bundle_old, service_license_bundle_new):
    cluster_old = service_license_bundle_old.cluster_create(name="license_upgrade_service_old")
    service_license_bundle_new.cluster_create(name="license_upgrade_service")
    with allure.step("Add first service without license"):
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster_old.id).open()
        cluster_service_page.add_service_by_name(service_name="service_1 - 1.2")

    with allure.step("Add second service with license"):
        license_dialog_window = add_service_and_get_license(page=cluster_service_page, service_name="service_2 - 1.2")
        license_text = license_dialog_window.get_text()
        assert (
            license_text == OLD_CLUSTER_SECOND_LICENSE
        ), f"Unexpected license, actual text: {license_text}\nexpected text: {OLD_CLUSTER_SECOND_LICENSE}"
        license_dialog_window.accept_license()

    with allure.step("Add second service with license which will the same after update"):
        license_dialog_window = add_service_and_get_license(page=cluster_service_page, service_name="service_3 - 1.2")
        license_text = license_dialog_window.get_text()
        assert (
            license_text == OLD_CLUSTER_THIRD_LICENSE
        ), f"Unexpected license, actual text: {license_text}\nexpected text: {OLD_CLUSTER_THIRD_LICENSE}"
        license_dialog_window.accept_license()

    with allure.step("Add third service with license which will change after update"):
        license_dialog_window = add_service_and_get_license(page=cluster_service_page, service_name="service_4 - 1.2")
        license_text = license_dialog_window.get_text()
        assert (
            license_text == OLD_CLUSTER_THIRD_LICENSE
        ), f"Unexpected license, actual text: {license_text}\nexpected text: {OLD_CLUSTER_THIRD_LICENSE}"
        license_dialog_window.accept_license()

    with allure.step("Run upgrade cluster and reject second license"):
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row_with_upgrade = cluster_page.get_row_by_cluster_name(cluster_old.name)
        cluster_page.run_upgrade_with_service_license(row_with_upgrade, "upgrade_with_service_license")

        license_dialog_header = cluster_page.get_service_license_dialog_header()
        license_dialog_window = cluster_page.get_service_license_dialog()
        license_dialog_window.accept_license()

        _wait_another_license_dialog_appear(cluster_page=cluster_page, old_license_dialog_header=license_dialog_header)
        license_dialog_window = cluster_page.get_service_license_dialog()
        license_dialog_window.reject_license()

    with allure.step("Check that cluster state did not change"):
        check_cluster_upgraded(app_fs, cluster_old.name, "created")

    with allure.step("Run upgrade cluster and accept all"):
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row_with_upgrade = cluster_page.get_row_by_cluster_name(cluster_old.name)
        cluster_page.run_upgrade_with_service_license(row_with_upgrade, "upgrade_with_service_license")

        license_dialog_window = cluster_page.get_service_license_dialog()
        license_dialog_window.accept_license()
        cluster_page.confirm_upgrade()

        cluster_old.reread()
        check_cluster_upgraded(app_fs, cluster_old.name, "upgraded")


def _wait_another_license_dialog_appear(cluster_page: ClusterListPage, old_license_dialog_header: str):
    """
    This method should be used in case when in one action we have few service license dialogs one by one
    Appearing new license dialog can take a few moments
    """

    def _wait_new_license_dialog():
        assert (
            actual_status := cluster_page.get_service_license_dialog_header()
        ) != old_license_dialog_header, f'Service license dialog header should be changed\nHeader "{actual_status}"'

    wait_until_step_succeeds(_wait_new_license_dialog, timeout=2, period=0.5)
