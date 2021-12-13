"""Common fixtures for the functional tests"""
from typing import Union

import pytest
from _pytest.python import FunctionDefinition, Module

from tests.conftest import CLEAN_ADCM_PARAM, DUMMY_DATA_FULL_PARAM

only_clean_adcm = pytest.mark.only_clean_adcm

ONLY_CLEAN_MARK = "only_clean_adcm"

CLEAN_ADCM_PARAMS = [CLEAN_ADCM_PARAM]
CLEAN_AND_DIRTY_PARAMS = [CLEAN_ADCM_PARAM, DUMMY_DATA_FULL_PARAM]


def _marker_in_node(mark: str, node: Union[FunctionDefinition, Module]) -> bool:
    """Check if mark is in own_markers of a node"""
    return any(marker.name == mark for marker in node.own_markers)


def pytest_generate_tests(metafunc):
    """
    Parametrize tests
    """
    if "additional_adcm_init_config" in metafunc.fixturenames:
        if _marker_in_node(ONLY_CLEAN_MARK, metafunc.definition) or (
            (parent := metafunc.definition.parent) and _marker_in_node(ONLY_CLEAN_MARK, parent)
        ):
            values = CLEAN_ADCM_PARAMS
        else:
            values = CLEAN_AND_DIRTY_PARAMS

        metafunc.parametrize("additional_adcm_init_config", values, scope="session")
