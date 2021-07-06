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
# pylint: disable=W0611, W0621
import time

import adcm_client.base
import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, Provider
from adcm_pytest_plugin.utils import get_data_dir


@pytest.fixture(scope="module")
def bundle(sdk_client_fs: ADCMClient) -> Bundle:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__))
    bundle.provider_create(name="first_p")
    bundle.provider_create(name="second_p")
    bundle.provider_create(name="third_p")
    bundle.provider_create(name="forth_p")
    return bundle


@pytest.fixture(scope="module")
def first_p(bundle: Bundle):
    return bundle.provider(name="first_p")


@pytest.fixture(scope="module")
def second_p(bundle: Bundle):
    return bundle.provider(name="second_p")


@pytest.fixture(scope="module")
def third_p(bundle: Bundle):
    return bundle.provider(name="third_p")


@pytest.fixture(scope="module")
def forth_p(bundle: Bundle):
    return bundle.provider(name="forth_p")


def test_create_one_host(second_p: Provider):
    """Test scenario:

    1. Create three providers
    2. Create host on one of the providers
    3. Ensure host exists
    """
    HOSTNAME = "second_h"
    with allure.step('Run action create host'):
        second_p.action(name="create_host").run(config_diff={'fqdn': HOSTNAME}).try_wait()
        second_h = second_p.host(fqdn=HOSTNAME)
    with allure.step('Check if host is created'):
        assert second_h.provider().id == second_p.id
        assert second_h.fqdn == HOSTNAME


def test_create_multi_host_and_delete_one(first_p: Provider, third_p: Provider):
    """Test scenario:

    1. Create three providers
    2. Create two host from first providers
    3. Create one host from third provider
    4. Remove one of host binded to first provider
    5. Check that host has been removed
    6. Check that other hosts still there.
    """
    with allure.step('Create two host from first providers'):
        first_p.action(name="create_host").run(config_diff={'fqdn': "one_one"}).try_wait()
        first_p.action(name="create_host").run(config_diff={'fqdn': "one_two"}).try_wait()
    with allure.step('Create one host from third provider'):
        third_p.action(name="create_host").run(config_diff={'fqdn': "three_one"}).try_wait()
    with allure.step('Remove one of host binded to first provider'):
        one_two = first_p.host(fqdn="one_two")
        one_two.action(name="remove_host").run().try_wait()
    with allure.step('Check that host has been removed'):
        assert first_p.host(fqdn="one_one").fqdn == "one_one"
    with allure.step('Check that other hosts still there'):
        assert third_p.host(fqdn="three_one").fqdn == "three_one"
        with pytest.raises(adcm_client.base.ObjectNotFound):
            first_p.host(fqdn="one_two")


def _wait_for_object(f, timeout=10, **kwargs):
    t = 0
    obj = None
    while (t < 10 and obj is None):
        try:
            obj = f(**kwargs)
        except adcm_client.base.ObjectNotFound:
            pass
        time.sleep(0.1)
        t = t + 0.1
    if obj is None:
        raise adcm_client.base.ObjectNotFound
    return obj


def test_check_host_lock_during_operations(forth_p: Provider):
    """Test scenario:

    1. Create provider
    2. Create host first host on provider
    3. Run job that creates the second host on provider
    4. Wait until second host will be created.
    5. Check that both host has "locked" state
    6. Wait for job to be finished without erros
    7. Check that both hosts is in "created" state
    8. Run remove action on one of hosts
    9. Check that host under action is "locked", while other host is "created"
    10. Wait for job to be finished without errors
    11. Check that remaining host is in "created" state.
    """
    with allure.step('Create host first host on provider'):
        forth_p.action(name="create_host").run(config_diff={'fqdn': "forth_one"}).try_wait()
    with allure.step('Run job that creates the second host on provider'):
        job = forth_p.action(name="create_host").run(config={'fqdn': "forth_two", 'sleep': 2})
    with allure.step('Wait until second host will be created'):
        forth_two_h = _wait_for_object(forth_p.host, fqdn='forth_two')
        forth_one_h = forth_p.host(fqdn='forth_one')
    with allure.step('Check that both host has "locked" state'):
        assert forth_one_h.state == 'locked'
        assert forth_two_h.state == 'locked'
    with allure.step('Wait for job to be finished without erros'):
        job.try_wait()
    with allure.step('Check that both hosts is in "created" state'):
        forth_one_h.reread()
        forth_two_h.reread()
        assert forth_one_h.state == 'created'
        assert forth_two_h.state == 'created'
    with allure.step('Run remove action on one of hosts'):
        job = forth_one_h.action(name="remove_host").run(config={"sleep": 2})
    with allure.step('Check that host under action is "locked", while other host is "created"'):
        forth_one_h.reread()
        forth_two_h.reread()
        assert forth_one_h.state == 'locked'
        assert forth_two_h.state == 'created'
    with allure.step('Wait for job to be finished without errors'):
        job.try_wait()
    with allure.step('Check that remaining host is in "created" state'):
        forth_two_h.reread()
        assert forth_two_h.state == 'created'
