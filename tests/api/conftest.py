"""ADCM api tests fixtures"""
import os

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster

from tests.api.steps.asserts import BodyAssertionError
from tests.api.steps.common import assume_step
from tests.api.utils.api_objects import ADCMTestApiWrapper


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
def prepare_basic_adcm_data(sdk_client_fs: ADCMClient):
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
    for i in range(3):
        provider = provider_bundle.provider_prototype().provider_create(f"provider_{i}")
        provider.host_create(fqdn=f"host_fqdn_{i}")
        cluster: Cluster = cluster_bundle.cluster_prototype().cluster_create(name=f"cluster_{i}")
        for j in range(6)[1:]:
            cluster.service_add(name=f"service_{j}")


@pytest.fixture()
def adcm_api_fs(sdk_client_fs, prepare_basic_adcm_data) -> ADCMTestApiWrapper:  # pylint: disable=redefined-outer-name
    """Runs ADCM container with previously initialized image.
    Returns authorized instance of ADCMTestApiWrapper object
    """
    return ADCMTestApiWrapper(adcm_api_wrapper=sdk_client_fs._api)  # pylint: disable=protected-access


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
