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
from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from .utils import prepare_cluster_and_get_config

pytestmark = [pytest.mark.usefixtures("login_to_adcm_over_api")]


@parametrize_by_data_subdirs(__file__, "false")
def test_required_field_false(sdk_client_fs: ADCMClient, path, app_fs):
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    with allure.step('Check that if required is false and field is empty save button active'):
        assert config.save_button_status()


@parametrize_by_data_subdirs(__file__, "true")
def test_required_field_true(sdk_client_fs: ADCMClient, path, app_fs):
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    with allure.step('Check that if required is true and field is empty save button not active'):
        assert not config.save_button_status()
