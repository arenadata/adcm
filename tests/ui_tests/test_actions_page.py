import time

import allure
import pytest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils

from tests.ui_tests.app.actions_page import ActionPage

# pylint: disable=W0621,C0301


@allure.step("Upload bundle and create cluster")
@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient):
    bundle_dir = utils.get_data_dir(__file__, "nothing_happens")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    return bundle.cluster_create(utils.random_string())


@allure.step("Open ADCM tab Action")
@pytest.fixture()
def cluster_action_page(app_fs, login_to_adcm, cluster):
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


@allure.step("Check if verbosity is {verbose_state}")
def check_verbosity(log, verbose_state):
    assert ("verbosity: 4" in log.content) is verbose_state


def test_check_verbose_checkbox_of_action_run_form_is_displayed(action_page):
    with allure.step("Check if verbose checkbox is displayed in popup from Action page"):
        assert (action_page.check_verbose_chbx_displayed()), "Verbose checkbox is not displayed in the popup"


@pytest.mark.parametrize("verbose_state", [True, False], ids=["verbose_state_true", "verbose_state_false"])
def test_check_verbose_info_of_action_run_form(action_page, cluster, verbose_state):
    action_page.run_action(is_verbose=verbose_state)
    job = wait_for_job_creation(cluster)
    log = job.log(job_id=job.id, log_id=job.log_list()[0].id)
    check_verbosity(log, verbose_state)
