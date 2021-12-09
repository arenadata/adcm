"""Common fixtures for the functional tests"""
import pytest

from tests.conftest import CLEAN_ADCM_PARAM, DUMMY_DATA_PARAM

only_clean_adcm = pytest.mark.only_clean_adcm


CLEAN_ADCM_PARAMS = [CLEAN_ADCM_PARAM]
CLEAN_AND_DIRTY_PARAMS = [CLEAN_ADCM_PARAM, DUMMY_DATA_PARAM]


def pytest_generate_tests(metafunc):
    """
    Parametrize tests
    """
    if "additional_adcm_init_config" in metafunc.fixturenames:
        if "only_clean_adcm" in metafunc.definition.own_markers:
            values = CLEAN_ADCM_PARAMS
        else:
            values = CLEAN_AND_DIRTY_PARAMS

        metafunc.parametrize("additional_adcm_init_config", values, scope="session")
