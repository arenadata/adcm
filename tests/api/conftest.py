"""ADCM api tests fixtures"""
import os

import allure
import pytest
from _pytest.config import Config
from adcm_client.objects import ADCMClient, Cluster, Service
from adcm_pytest_plugin.utils import get_or_add_service

from tests.api.steps.asserts import BodyAssertionError
from tests.api.steps.common import assume_step
from tests.api.utils.api_objects import ADCMTestApiWrapper


def pytest_configure(config: Config):
    """
    Exclude prepare test data classes from pytest collect
    """
    config.inicfg["python_classes"] = "*Test"


def pytest_addoption(parser):
    """
    Additional options for ADCM api testing
    """
    parser.addoption(
        "--disable-soft-assert",
        action="store_true",
        help="This option is needed to disable soft assert in 'flexible_assert_step' fixture",
    )


@pytest.fixture()
def prepare_basic_adcm_data(sdk_client_fs: ADCMClient) -> ADCMClient:
    """
    Prepare ADCM with dummy provider and cluster bundle.
    Add 3 providers, 3 hosts, 3 clusters, 5 services for each cluster
    """
    # TODO: In the future use pre-filled ADCM

    cluster_bundle = sdk_client_fs.upload_from_fs(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata/bundle_community/")
    )
    provider_bundle = sdk_client_fs.upload_from_fs(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata/provider/")
    )
    for i in range(6):
        provider = provider_bundle.provider_prototype().provider_create(f"provider_{i}")
        cluster: Cluster = cluster_bundle.cluster_prototype().cluster_create(name=f"cluster_{i}")
        hosts = [provider.host_create(fqdn=f"host_{provider.name}_{n}") for n in range(6)]
        hc_list = []
        for host in hosts:
            cluster.host_add(host)
            for j in range(4)[1:]:
                service: Service = get_or_add_service(cluster, f"service_{j}")
                for component in service.component_list():
                    hc_list.append((host, component))
        cluster.hostcomponent_set(*hc_list)
    return sdk_client_fs


@pytest.fixture()
def adcm_api_fs(prepare_basic_adcm_data) -> ADCMTestApiWrapper:  # pylint: disable=redefined-outer-name
    """Runs ADCM container with previously initialized image.
    Returns authorized instance of ADCMTestApiWrapper object
    """
    return ADCMTestApiWrapper(adcm_api_wrapper=prepare_basic_adcm_data._api)  # pylint: disable=protected-access


@pytest.fixture()
def flexible_assert_step(cmd_opts):
    """
    Returns either allure.step or assume_step context manager
    depending on option '--disable-soft-assert'
    """

    def _flexible_assert_step(title, assertion_error=BodyAssertionError):
        if cmd_opts.disable_soft_assert is True:
            return allure.step(title)
        return assume_step(title, assertion_error)

    return _flexible_assert_step
