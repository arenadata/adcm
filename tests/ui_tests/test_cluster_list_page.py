import allure
import pytest
from adcm_pytest_plugin import utils

from tests.ui_tests.app.page.cluster_list_page.cluster_list import ClusterListPage


@pytest.mark.parametrize("bundle_archive",
                         [
                             pytest.param(utils.get_data_dir(__file__, "cluster_community"), id="community"),
                             pytest.param(utils.get_data_dir(__file__, "cluster_enterprise"), id="enterprise")
                         ],
                         indirect=True)
def test_check_cluster_list_page_with_cluster_creating(app_fs, auth_to_adcm, bundle_archive):
    edition = bundle_archive.split("cluster_")[2][:-4]
    cluster_params = {'bundle': f'test_cluster 1.5 {edition}', 'state': 'created'}
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    with allure.step("Check no cluster rows"):
        assert len(cluster_page.get_all_cluster_rows()) == 0, "There should be no row with clusters"
    cluster_page.download_cluster(bundle_archive, is_license=True if edition == "enterprise" else False)
    with allure.step("Check uploaded cluster"):
        assert len(cluster_page.get_all_cluster_rows()) == 1, "There should be 1 row with cluster"
        uploaded_cluster = cluster_page.get_cluster_info_from_row(0)
        assert cluster_params['bundle'] == uploaded_cluster['bundle'], \
            f"Cluster bundle should be {cluster_params['bundle']} and not {uploaded_cluster['bundle']}"
        assert cluster_params['state'] == uploaded_cluster['state'], \
            f"Cluster state should be {cluster_params['state']} and not {uploaded_cluster['state']}"
