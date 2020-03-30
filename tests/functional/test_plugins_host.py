# pylint: disable=W0611, W0621
import time
import pytest
import adcm_client.base
from adcm_client.objects import ADCMClient, Bundle, Provider
from adcm_pytest_plugin.utils import get_data_dir


@pytest.fixture(scope="module")
def bundle(sdk_client_ms: ADCMClient) -> Bundle:
    bundle = sdk_client_ms.upload_from_fs(get_data_dir(__file__))
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
    HOSTNAME = "second_h"

    second_p.action(name="create_host").run(config_diff={'fqdn': HOSTNAME}).try_wait()
    second_h = second_p.host(fqdn=HOSTNAME)

    assert second_h.provider().id == second_p.id
    assert second_h.fqdn == HOSTNAME


def test_create_multi_host_and_delete_one(first_p: Provider, third_p: Provider):
    first_p.action(name="create_host").run(config_diff={'fqdn': "one"}).try_wait()
    first_p.action(name="create_host").run(config_diff={'fqdn': "one_two"}).try_wait()
    third_p.action(name="create_host").run(config_diff={'fqdn': "three"}).try_wait()

    one_two = first_p.host(fqdn="one_two")
    one_two.action(name="remove_host").run().try_wait()
    one = first_p.host(fqdn="one")
    assert one.fqdn == "one"
    three = third_p.host(fqdn="three")
    assert three.fqdn == "three"


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
    forth_p.action(name="create_host").run(config_diff={'fqdn': "forth_one"}).try_wait()
    job = forth_p.action(name="create_host").run(config={'fqdn': "forth_two", 'sleep': 2})

    forth_two_h = _wait_for_object(forth_p.host, fqdn='forth_two')
    forth_one_h = forth_p.host(fqdn='forth_one')

    assert forth_one_h.state == 'locked'
    assert forth_two_h.state == 'locked'

    job.try_wait()

    forth_one_h.reread()
    forth_two_h.reread()
    assert forth_one_h.state == 'created'
    assert forth_two_h.state == 'created'

    job = forth_one_h.action(name="remove_host").run(config={"sleep": 2})

    forth_one_h.reread()
    forth_two_h.reread()
    assert forth_one_h.state == 'locked'
    assert forth_two_h.state == 'created'

    job.try_wait()

    forth_two_h.reread()
    assert forth_two_h.state == 'created'
