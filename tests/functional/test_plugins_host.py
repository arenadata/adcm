# pylint: disable=W0611, W0621
import pytest
from adcm_client.objects import ADCMClient, Bundle, Provider
from adcm_pytest_plugin.utils import get_data_dir


@pytest.fixture(scope="module")
def bundle(sdk_client_ms: ADCMClient) -> Bundle:
    bundle = sdk_client_ms.upload_from_fs(get_data_dir(__file__))
    bundle.provider_create(name="first_p")
    bundle.provider_create(name="second_p")
    bundle.provider_create(name="third_p")
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


def test_create_one_host(second_p: Provider):
    HOSTNAME = "second_h"

    second_p.action(name="create_host").run(config={'fqdn': HOSTNAME}).try_wait()
    second_h = second_p.host(fqdn=HOSTNAME)

    assert second_h.provider().id == second_p.id
    assert second_h.fqdn == HOSTNAME


def test_create_multi_host_and_delete_one(first_p: Provider, third_p: Provider):
    first_p.action(name="create_host").run(config={'fqdn': "one"}).try_wait()
    first_p.action(name="create_host").run(config={'fqdn': "one_two"}).try_wait()
    third_p.action(name="create_host").run(config={'fqdn': "three"}).try_wait()

    one_two = first_p.host(fqdn="one_two")
    one_two.action(name="remove_host").run().try_wait()
    one = first_p.host(fqdn="one")
    assert one.fqdn == "one"
    three = third_p.host(fqdn="three")
    assert three.fqdn == "three"
