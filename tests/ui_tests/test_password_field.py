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
from adcm_pytest_plugin.utils import get_data_dir

from tests.ui_tests.app.locators import Common
from tests.ui_tests.utils import prepare_cluster_and_get_config

pytestmark = [pytest.mark.usefixtures("login_to_adcm_over_api")]


def test_password_noconfirm_false_required_false(sdk_client_fs: ADCMClient, app_fs):
    path = get_data_dir(__file__) + "/password_no_confirm_false_required_false"
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    with allure.step('Check save button status for no password confirmation is false and required is false'):
        assert config.save_button_status()


def test_password_noconfirm_false_required_true(sdk_client_fs: ADCMClient, app_fs):
    path = get_data_dir(__file__) + "/password_no_confirm_false_required_true"
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    with allure.step('Check save button status for no password confirmation is true and required is false'):
        assert not config.save_button_status()
    with allure.step('Check that we have two frontend errors for password and confirmation password field'):
        password_field = config.get_password_elements()[0]
        forms = [form.text for form in password_field.find_elements(*Common.mat_form_field)]
        assert len(forms) == 2, forms
        assert 'Field [password] is required!' in forms, forms
        assert 'Confirm [password] is required!' in forms, forms


def test_password_noconfirm_true_required_false(sdk_client_fs: ADCMClient, app_fs):
    path = get_data_dir(__file__) + "/password_no_confirm_true_required_false"
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    with allure.step('Check save button status for no password confirmation is false and required is false'):
        assert config.save_button_status()
        password_field = config.get_password_elements()[0]
        forms = [form.text for form in password_field.find_elements(*Common.mat_form_field)]
        assert len(forms) == 1, forms


def test_password_noconfirm_true_required_true(sdk_client_fs: ADCMClient, app_fs):
    path = get_data_dir(__file__) + "/password_no_confirm_true_required_true"
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    with allure.step('Check save button status for no password confirmation is false and required is false'):
        assert not config.save_button_status()
        password_field = config.get_password_elements()[0]
        forms = [form.text for form in password_field.find_elements(*Common.mat_form_field)]
        assert len(forms) == 1, forms
        assert forms[0] == 'Field [password] is required!', forms
