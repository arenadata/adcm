import time

import allure
import pytest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils

from tests.ui_tests.app.actions_page import ActionPage


@allure.step('Create cluster')
@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient):
    bundle_dir = utils.get_data_dir(__file__, "nothing_happens")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    return bundle.cluster_create(utils.random_string())


@allure.step('Open ADCM tab Action')
@pytest.fixture()
def action_page(app_fs, login_to_adcm, cluster):
    return ActionPage(app_fs.driver, f"{app_fs.adcm.url}/cluster/{cluster.cluster_id}/action")


def wait_for_task(cluster, interval=1, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            return cluster.action(name="test_action").task()
        except ObjectNotFound:
            pass
        time.sleep(interval)


def test_check_verbose_checkbox_of_action_run_form_is_displayed(action_page):
    with allure.step('Check if verbose checkbox is displayed in popup from Action page'):
        assert action_page.check_verbose_chbx_displayed(), 'Verbose checkbox doesnt displayed in popup'


@pytest.mark.parametrize("verbose_state",
                         [True,
                          False],
                         ids=['verbose_state_true',
                              'verbose_state_false'])
def test_check_verbose_info_of_action_run_form(action_page, cluster, verbose_state):
    action_page.run_action(is_verbose=verbose_state)
    with allure.step(f'Check if verbosity is {verbose_state}'):
        task = wait_for_task(cluster)
        job = task.job()
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[0].id)
        assert ('verbosity: 4' in log.content) is verbose_state
