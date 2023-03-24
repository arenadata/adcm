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

import allure
import pytest
from adcm_client.objects import Cluster

from tests.library.retry import should_become_truth
from tests.ui_tests.app.page.cluster.page import ClusterMainPage
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.job.page import JobPageStdout
from tests.ui_tests.concerns.common import BUNDLES_DIR
from tests.ui_tests.core.elements import Link, ListOfElements

SIMPLE_ACTION = "simple_sleep"
COMPLEX_ACTION = "complex_sleep"


@pytest.fixture()
def clusters(sdk_client_fs, generic_provider) -> tuple[Cluster, Cluster]:
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "action_concerns")
    cluster_1 = bundle.cluster_create("Cluster 1")
    cluster_2 = bundle.cluster_create("Cluster 2")

    cluster_1.host_add(generic_provider.host_create("host-1"))
    cluster_2.host_add(generic_provider.host_create("host-2"))

    for cluster in cluster_1, cluster_2:
        cluster.service_add(name="first_service")
        cluster.service_add(name="second_service")

    return cluster_1, cluster_2


@pytest.mark.usefixtures("_login_to_adcm_over_api")
def test_running_job_concern_links(app_fs, clusters):  # pylint: disable=redefined-outer-name
    cluster_1, cluster_2 = clusters

    with allure.step("Run 1 action and check job's content after following concern link"):
        clusters_page = ClusterListPage(driver=app_fs.driver, base_url=app_fs.adcm.url).open()
        task = cluster_1.action(name=SIMPLE_ACTION).run()
        popover = clusters_page.hover_concern_button(clusters_page.get_row_by_cluster_name(cluster_1.name))
        assert len(popover.concerns) == 1
        links: ListOfElements[Link] = popover.concerns.first.links
        assert len(links) == 2
        links.named(SIMPLE_ACTION).click()
        job_info = (
            JobPageStdout.from_page(clusters_page, job_id=task.job().id).wait_page_is_opened(timeout=2).get_job_info()
        )
        assert job_info.name == SIMPLE_ACTION
        assert job_info.invoker_objects == cluster_1.name
        task.wait()

    with allure.step("Run 2 simple actions and open job of the first launched via concern's link"):
        clusters_page.open()
        task_of_cluster_2 = cluster_2.action(name=SIMPLE_ACTION).run()
        task_of_cluster_1 = cluster_1.action(name=SIMPLE_ACTION).run()
        popover = clusters_page.hover_concern_button(clusters_page.get_row_by_cluster_name(cluster_2.name))
        popover.concerns.first.links.named(SIMPLE_ACTION).click()
        job_info = (
            JobPageStdout.from_page(clusters_page, job_id=task_of_cluster_2.job().id)
            .wait_page_is_opened(timeout=2)
            .get_job_info()
        )
        assert job_info.name == SIMPLE_ACTION
        assert job_info.invoker_objects == cluster_2.name
        task_of_cluster_2.wait()

    with allure.step("Run job and follow concern's link to cluster"):
        clusters_page.open()
        cluster_2.action(name=SIMPLE_ACTION).run()
        popover = clusters_page.hover_concern_button(clusters_page.get_row_by_cluster_name(cluster_2.name))
        popover.concerns.first.links.named(cluster_2.name).click()
        detail_page = ClusterMainPage.from_page(clusters_page, cluster_id=cluster_2.id).wait_page_is_opened()
        detail_page.check_all_elements()

    with allure.step("Run 'task' action, wait for 2nd job and open it via concern link"):
        second_step_name = "step_2"
        task_of_cluster_1.wait()
        clusters_page.open()
        task = cluster_1.action(name=COMPLEX_ACTION).run()
        second_job = next(j for j in task.job_list() if j.display_name == second_step_name)
        should_become_truth(lambda: second_job.reread() or second_job.status == "running", retries=15, period=0.5)
        popover = clusters_page.hover_concern_button(clusters_page.get_row_by_cluster_name(cluster_1.name))
        popover.concerns.first.links.named(COMPLEX_ACTION).click()
        job_info = (
            JobPageStdout.from_page(clusters_page, job_id=second_job.id).wait_page_is_opened(timeout=2).get_job_info()
        )
        assert job_info.name == second_step_name
        assert job_info.invoker_objects == cluster_1.name
