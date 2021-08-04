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

import os

import allure
import pytest
from adcm_client.objects import (
    ADCMClient,
    Bundle,
)
from adcm_pytest_plugin import utils

from tests.ui_tests.app.page.admin_intro.page import AdminIntroPage
from tests.ui_tests.app.page.cluster.page import (
    ClusterImportPage,
    ClusterConfigPage,
    ClusterMainPage,
    ClusterServicesPage,
)
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage

BUNDLE_COMMUNITY = "cluster_community"
BUNDLE_ENTERPRISE = "cluster_enterprise"
BUNDLE_IMPORT = "cluster_to_import"
BUNDLE_UPGRADE = "upgradable_cluster"
CLUSTER_NAME = "Test cluster"


@pytest.fixture()
def _create_community_cluster(sdk_client_fs: ADCMClient, app_fs, auth_to_adcm):
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    bundle.cluster_create(name=CLUSTER_NAME)


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), data_dir_name))


@pytest.mark.parametrize(
    "bundle_archive",
    [
        pytest.param(utils.get_data_dir(__file__, BUNDLE_COMMUNITY), id="community"),
        pytest.param(utils.get_data_dir(__file__, BUNDLE_ENTERPRISE), id="enterprise"),
    ],
    indirect=True,
)
def test_check_cluster_list_page_with_cluster_creating(
    app_fs, login_to_adcm_over_api, bundle_archive
):
    edition = bundle_archive.split("cluster_")[2][:-4]
    cluster_params = {
        "bundle": f"test_cluster 1.5 {edition}",
        "description": "Test",
        "state": "created",
    }
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    with allure.step("Check no cluster rows"):
        assert len(cluster_page.table.get_all_rows()) == 0, "There should be no row with clusters"
    cluster_page.create_cluster(
        bundle_archive, cluster_params['description'], is_license=bool(edition == "enterprise")
    )
    with allure.step("Check uploaded cluster"):
        assert len(cluster_page.table.get_all_rows()) == 1, "There should be 1 row with cluster"
        uploaded_cluster = cluster_page.get_cluster_info_from_row(0)
        assert cluster_params['bundle'] == uploaded_cluster['bundle'], (
            f"Cluster bundle should be {cluster_params['bundle']} and "
            f"not {uploaded_cluster['bundle']}"
        )
        assert cluster_params['description'] == uploaded_cluster['description'], (
            f"Cluster description should be {cluster_params['description']} and "
            f"not {uploaded_cluster['description']}"
        )
        assert (
            cluster_params['state'] == uploaded_cluster['state']
        ), f"Cluster state should be {cluster_params['state']} and not {uploaded_cluster['state']}"


def test_check_cluster_list_page_pagination(
    sdk_client_fs: ADCMClient, app_fs, login_to_adcm_over_api
):
    params = {"fist_page_cluster_amount": 10, "second_page_cluster_amount": 1}
    with allure.step("Create 11 clusters"):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
        for i in range(11):
            bundle.cluster_create(name=f"Test cluster {i}")
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    cluster_page.close_info_popup()
    with allure.step("Check pagination"):
        with cluster_page.table.wait_rows_change():
            cluster_page.table.click_page_by_number(2)
        assert (
            len(cluster_page.table.get_all_rows()) == params["second_page_cluster_amount"]
        ), f"Second page should contains {params['second_page_cluster_amount']}"
        with cluster_page.table.wait_rows_change():
            cluster_page.table.click_page_by_number(1)
        assert (
            len(cluster_page.table.get_all_rows()) == params["fist_page_cluster_amount"]
        ), f"First page should contains {params['fist_page_cluster_amount']}"
        with cluster_page.table.wait_rows_change():
            cluster_page.table.click_next_page()
        assert (
            len(cluster_page.table.get_all_rows()) == params["second_page_cluster_amount"]
        ), f"Next page should contains {params['second_page_cluster_amount']}"
        with cluster_page.table.wait_rows_change():
            cluster_page.table.click_previous_page()
        assert (
            len(cluster_page.table.get_all_rows()) == params["fist_page_cluster_amount"]
        ), f"Previous page should contains {params['fist_page_cluster_amount']}"


@pytest.mark.usefixtures("_create_community_cluster")
def test_check_cluster_list_page_action_run(app_fs):
    params = {"action_name": "test_action", "expected_state": "installed"}
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    row = cluster_page.table.get_all_rows()[0]
    with cluster_page.wait_cluster_state_change(row):
        cluster_page.run_action_in_cluster_row(row, params["action_name"])
    with allure.step("Check state has changed"):
        assert (
            cluster_page.get_cluster_state_from_row(row) == params["expected_state"]
        ), f"Cluster state should be {params['expected_state']}"
    with allure.step("Check success job"):
        assert (
            cluster_page.header.get_success_job_amount_from_header() == "1"
        ), "There should be 1 success job in header"


def test_check_cluster_list_page_import_run(sdk_client_fs: ADCMClient, app_fs, auth_to_adcm):
    params = {"import_cluster_name": "Import cluster"}
    with allure.step("Create main cluster"):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
        bundle.cluster_create(name=CLUSTER_NAME)
    with allure.step("Create cluster to import"):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_IMPORT)
        bundle.cluster_create(name=params["import_cluster_name"])
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    row = cluster_page.get_row_by_cluster_name(CLUSTER_NAME)
    cluster_page.click_import_btn_in_row(row)
    import_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, 1)
    import_page.wait_page_is_opened()
    with allure.step("Check import on import page"):
        assert (
            len(import_page.get_import_items()) == 1
        ), "Cluster import page should contain 1 import"


@pytest.mark.usefixtures("_create_community_cluster")
def test_check_cluster_list_page_open_cluster_config(app_fs):
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    row = cluster_page.table.get_all_rows()[0]
    cluster_page.click_config_button_in_row(row)
    ClusterConfigPage(app_fs.driver, app_fs.adcm.url, 1).wait_page_is_opened()


@pytest.mark.usefixtures("_create_community_cluster")
def test_check_cluster_list_page_open_cluster_main(app_fs):
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    row = cluster_page.table.get_all_rows()[0]
    cluster_page.click_cluster_name_in_row(row)
    ClusterMainPage(app_fs.driver, app_fs.adcm.url, 1).wait_page_is_opened()


@pytest.mark.usefixtures("_create_community_cluster")
def test_check_cluster_list_page_delete_cluster(app_fs):
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    row = cluster_page.table.get_all_rows()[0]
    with cluster_page.table.wait_rows_change():
        cluster_page.delete_cluster_by_row(row)
    with allure.step("Check there are no rows"):
        assert len(cluster_page.table.get_all_rows()) == 0, "Cluster table should be empty"


@pytest.mark.usefixtures("_create_community_cluster")
def test_check_cluster_main_page_open_by_tab(app_fs):
    cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, 1).open()
    cluster_config_page.open_main_tab()
    cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, 1)
    cluster_main_page.wait_page_is_opened()
    cluster_main_page.check_all_elements()


@pytest.mark.usefixtures("_create_community_cluster")
def test_check_cluster_admin_page_open_by_toolbar(app_fs):
    cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, 1).open()
    cluster_main_page.toolbar.click_admin_link()
    AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()


@pytest.mark.usefixtures("_create_community_cluster")
def test_check_cluster_main_page_open_by_toolbar(app_fs):
    params = {"cluster_list_name": "CLUSTERS"}
    cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, 1).open()
    cluster_main_page.toolbar.click_link_by_name(params["cluster_list_name"])
    ClusterListPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
    cluster_import_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, 1).open()
    cluster_import_page.toolbar.click_link_by_name(CLUSTER_NAME)
    cluster_main_page.wait_page_is_opened()


def test_check_cluster_run_upgrade_on_cluster_page_by_toolbar(sdk_client_fs, app_fs, auth_to_adcm):
    params = {
        "upgrade_cluster_name": "upgrade cluster",
        "upgrade": "upgrade 2",
        "state": "upgradated",
    }
    with allure.step("Create main cluster"):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
        bundle.cluster_create(name=CLUSTER_NAME)
    with allure.step("Create cluster to upgrade"):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_UPGRADE)
        bundle.cluster_create(name=params["upgrade_cluster_name"])
    main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, 2).open()
    main_page.toolbar.run_upgrade(params["upgrade_cluster_name"], params["upgrade"])
    with allure.step("Check that cluster has been upgraded"):
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.get_row_by_cluster_name(params["upgrade_cluster_name"])
        assert (
            cluster_page.get_cluster_state_from_row(row) == params["state"]
        ), f"Cluster state should be {params['state']}"


@pytest.mark.usefixtures("_create_community_cluster")
def test_check_cluster_run_action_on_cluster_page_by_toolbar(app_fs):
    params = {"action_name": "test_action"}
    cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, 1).open()
    cluster_main_page.toolbar.run_action(CLUSTER_NAME, params["action_name"])
    with allure.step("Check success job"):
        assert (
            cluster_main_page.header.get_in_progress_job_amount_from_header() == "1"
        ), "There should be 1 in progress job in header"


@pytest.mark.usefixtures("_create_community_cluster")
def test_check_cluster_service_page_open_by_tab(app_fs):
    cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, 1).open()
    cluster_config_page.open_services_tab()
    cluster_main_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, 1)
    cluster_main_page.wait_page_is_opened()
    cluster_main_page.check_all_elements()
