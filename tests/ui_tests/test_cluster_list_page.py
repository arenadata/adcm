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

from tests.ui_tests.app.page.cluster_list.page import ClusterListPage


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), data_dir_name))


@pytest.mark.parametrize(
    "bundle_archive",
    [
        pytest.param(utils.get_data_dir(__file__, "cluster_community"), id="community"),
        pytest.param(utils.get_data_dir(__file__, "cluster_enterprise"), id="enterprise"),
    ],
    indirect=True,
)
def test_check_cluster_list_page_with_cluster_creating(app_fs, auth_to_adcm, bundle_archive):
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


def test_check_cluster_list_page_pagination(sdk_client_fs: ADCMClient, app_fs, auth_to_adcm):
    params = {"fist_page_cluster_amount": 10, "second_page_cluster_amount": 1}
    with allure.step("Create 11 clusters"):
        bundle = cluster_bundle(sdk_client_fs, 'cluster_community')
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
