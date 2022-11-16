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

"""Common fixtures for the functional tests"""

import pytest
from tests.conftest import (
    CLEAN_ADCM_PARAM,
    DUMMY_DATA_FULL_PARAM,
    marker_in_node_or_its_parent,
)

only_clean_adcm = pytest.mark.only_clean_adcm

ONLY_CLEAN_MARK = "only_clean_adcm"

CLEAN_ADCM_PARAMS = [CLEAN_ADCM_PARAM]
CLEAN_AND_DIRTY_PARAMS = [CLEAN_ADCM_PARAM, DUMMY_DATA_FULL_PARAM]


def pytest_generate_tests(metafunc):
    """
    Parametrize tests
    """
    if "additional_adcm_init_config" in metafunc.fixturenames:
        if marker_in_node_or_its_parent(ONLY_CLEAN_MARK, metafunc.definition):
            values = CLEAN_ADCM_PARAMS
        else:
            values = CLEAN_AND_DIRTY_PARAMS

        metafunc.parametrize("additional_adcm_init_config", values, scope="session")
