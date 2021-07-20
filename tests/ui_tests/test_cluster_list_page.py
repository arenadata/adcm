import pytest
from adcm_pytest_plugin import utils

from tests.ui_tests.app.page.cluster_list_page.cluster_list import ClusterListPage


@pytest.mark.parametrize("bundle_archive",
                         [pytest.param(utils.get_data_dir(__file__, "cluster_community"), id="cluster_community",)],
                         indirect=True)
def test_check_cluster_list_page_with_cluster_creating(app_fs, auth_to_adcm, bundle_archive):
    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    cluster_page.download_cluster(bundle_archive)
    assert len(cluster_page.get_all_cluster_rows()) == 1
