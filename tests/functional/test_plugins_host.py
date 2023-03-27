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

"""Tests for adcm_host plugin"""

# pylint:disable=redefined-outer-name
import adcm_client.base
import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, Provider
from adcm_pytest_plugin.utils import get_data_dir, wait_until_step_succeeds


@pytest.fixture()
def bundle(sdk_client_fs: ADCMClient) -> Bundle:
    """Upload bundle and create 4 provider objects"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__))
    bundle.provider_create(name="first_p")
    bundle.provider_create(name="second_p")
    bundle.provider_create(name="third_p")
    bundle.provider_create(name="forth_p")
    return bundle


@pytest.fixture()
def first_p(bundle: Bundle):
    """First provider"""
    return bundle.provider(name="first_p")


@pytest.fixture()
def second_p(bundle: Bundle):
    """Second provider"""
    return bundle.provider(name="second_p")


@pytest.fixture()
def third_p(bundle: Bundle):
    """Third provider"""
    return bundle.provider(name="third_p")


@pytest.fixture()
def forth_p(bundle: Bundle):
    """Forth provider"""
    return bundle.provider(name="forth_p")


def test_create_one_host(second_p: Provider):
    """Test scenario:

    1. Create three providers
    2. Create host on one of the providers
    3. Ensure host exists
    """
    hostname = "second_h"
    with allure.step("Run action create host"):
        second_p.action(name="create_host").run(config_diff={"fqdn": hostname}).try_wait()
        second_h = second_p.host(fqdn=hostname)
    with allure.step("Check if host is created"):
        assert second_h.provider().id == second_p.id
        assert second_h.fqdn == hostname


def test_create_multi_host_and_delete_one(first_p: Provider, third_p: Provider):
    """Test scenario:

    1. Create three providers
    2. Create two host from first providers
    3. Create one host from third provider
    4. Remove one of host bound to first provider
    5. Check that host has been removed
    6. Check that other hosts still there.
    """
    with allure.step("Create two host from first providers"):
        first_p.action(name="create_host").run(config_diff={"fqdn": "one_one"}).try_wait()
        first_p.action(name="create_host").run(config_diff={"fqdn": "one_two"}).try_wait()
    with allure.step("Create one host from third provider"):
        third_p.action(name="create_host").run(config_diff={"fqdn": "three_one"}).try_wait()
    with allure.step("Remove one of host bound to first provider"):
        one_two = first_p.host(fqdn="one_two")
        one_two.action(name="remove_host").run().try_wait()
    with allure.step("Check that host has been removed"):
        assert first_p.host(fqdn="one_one").fqdn == "one_one"
    with allure.step("Check that other hosts still there"):
        assert third_p.host(fqdn="three_one").fqdn == "three_one"
        with pytest.raises(adcm_client.base.ObjectNotFound):
            first_p.host(fqdn="one_two")


def _assert_that_object_exists(get_object_func, *args, **kwargs):
    try:
        obj = get_object_func(*args, **kwargs)
    except adcm_client.base.ObjectNotFound as error:
        raise AssertionError("Object still not found") from error
    if obj is None:
        raise AssertionError("Object is None")


def test_check_host_lock_during_operations(forth_p: Provider):
    """Test scenario:

    1. Create provider
    2. Create host first host on provider
    3. Run job that creates the second host on provider
    4. Wait until second host will be created.
    5. Check that both host is locked
    6. Wait for job to be finished without errors
    7. Check that both hosts is free
    8. Run remove action on one of hosts
    9. Check that host under action is locked, while other host is free
    10. Wait for job to be finished without errors
    11. Check that remaining host is free.
    """
    with allure.step("Create host first host on provider"):
        forth_p.action(name="create_host").run(config_diff={"fqdn": "forth_one"}).try_wait()
    with allure.step("Run job that creates the second host on provider"):
        job = forth_p.action(name="create_host").run(config={"fqdn": "forth_two", "sleep": 2})
    with allure.step("Wait until second host will be created"):
        wait_until_step_succeeds(
            _assert_that_object_exists,
            period=0.5,
            get_object_func=forth_p.host,
            fqdn="forth_two",
        )
        forth_two_h = forth_p.host(fqdn="forth_two")
        forth_one_h = forth_p.host(fqdn="forth_one")
    with allure.step("Check that both host has is locked"):
        assert forth_one_h.locked is True
        assert forth_two_h.locked is True
    with allure.step("Wait for job to be finished without errors"):
        job.try_wait()
    with allure.step("Check that both hosts is free"):
        forth_one_h.reread()
        forth_two_h.reread()
        assert forth_one_h.locked is False
        assert forth_two_h.locked is False
    with allure.step("Run remove action on one of hosts"):
        job = forth_one_h.action(name="remove_host").run(config={"sleep": 2})
    with allure.step("Check that host under action is locked, while other host is free"):
        forth_one_h.reread()
        forth_two_h.reread()
        assert forth_one_h.locked is True
        assert forth_two_h.locked is False
    with allure.step("Wait for job to be finished without errors"):
        job.try_wait()
    with allure.step("Check that remaining host is free"):
        forth_two_h.reread()
        assert forth_two_h.locked is False
