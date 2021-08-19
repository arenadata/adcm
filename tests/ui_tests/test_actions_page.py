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

import time

import allure
import pytest
from adcm_client.base import (
    ObjectNotFound,
    WaitTimeout,
)
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils

from tests.ui_tests.app.actions_page import ActionPage

# pylint: disable=redefined-outer-name


@allure.step("Upload bundle and create cluster")
@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient):
    bundle_dir = utils.get_data_dir(__file__, "nothing_happens")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    return bundle.cluster_create(utils.random_string())


@allure.step("Open ADCM tab Action")
@pytest.fixture()
def cluster_action_page(app_fs, cluster, login_to_adcm_over_api):  # pylint: disable=unused-argument
    return ActionPage(app_fs.driver, url=app_fs.adcm.url, cluster_id=cluster.cluster_id)


@allure.step("Open ADCM tab Action")
def wait_for_job_creation(cluster, interval=1, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            task = cluster.action().task()
            return task.job()
        except ObjectNotFound:
            pass
        time.sleep(interval)
    raise WaitTimeout(f'Job has not been created for {timeout} seconds')


@allure.step("Check if verbosity is {verbose_state}")
def check_verbosity(log, verbose_state):
    assert ("verbosity: 4" in log.content) is verbose_state


def test_check_verbose_checkbox_of_action_run_form_is_displayed(cluster_action_page):
    with allure.step("Check if verbose checkbox is displayed in popup from Action page"):
        assert (
            cluster_action_page.check_verbose_chbx_displayed()
        ), "Verbose checkbox is not displayed in the popup"


@pytest.mark.parametrize(
    "verbose_state", [True, False], ids=["verbose_state_true", "verbose_state_false"]
)
def test_check_verbose_info_of_action_run_form(cluster_action_page, cluster, verbose_state):
    cluster_action_page.run_action(is_verbose=verbose_state)
    job = wait_for_job_creation(cluster)
    log = job.log(job_id=job.id, log_id=job.log_list()[0].id)
    check_verbosity(log, verbose_state)
