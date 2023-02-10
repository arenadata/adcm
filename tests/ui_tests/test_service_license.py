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
from adcm_client.objects import ADCMClient, Cluster
from adcm_pytest_plugin.utils import get_data_dir

from tests.ui_tests.app.page.cluster.page import ClusterServicesPage
from tests.ui_tests.app.page.common.dialogs.service_license import ServiceLicenseModal

FIRST_LICENSE_TEXT = "first license for service"
SECOND_LICENSE_TEXT = "second license for another service"


@pytest.fixture(name="service_license_cluster")
def bundle_with_first_license(sdk_client_fs: ADCMClient) -> Cluster:
    """Upload bundle with license"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "license1"))
    cluster = bundle.cluster_create(name="license_service")
    return cluster


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
        cluster_service_page.close_add_service_window()

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
        cluster_service_page.add_service_by_name(service_name="service_2 - 1.0")

    with allure.step("Delete service with license and add it again"):
        service_1 = cluster.service(name="service_1")
        cluster.service_delete(service_1)
        service_3 = cluster.service(name="service_3")
        cluster.service_delete(service_3)

        cluster_service_page.add_service_by_name(service_name="service_1 - 1.0")
        cluster_service_page.add_service_by_name(service_name="service_3 - 1.0")
