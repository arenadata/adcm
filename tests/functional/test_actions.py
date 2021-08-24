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

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils

from tests.ui_tests.test_actions_page import check_verbosity


@pytest.mark.parametrize("verbose_state", [True, False], ids=["verbose_state_true", "verbose_state_false"])
def test_check_verbose_option_of_action_run(sdk_client_fs: ADCMClient, verbose_state):
    """Test action run with verbose switch"""
    bundle_dir = utils.get_data_dir(__file__, "verbose_state")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name="dummy_action").run(verbose=verbose_state)
    with allure.step(f"Check if verbosity is {verbose_state}"):
        task.wait()
        log = task.job().log()
        check_verbosity(log, verbose_state)
