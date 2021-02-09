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
import coreapi
import pytest
# pylint: disable=W0611, W0621
from adcm_pytest_plugin import utils

from tests.library import steps
from tests.library.errorcodes import BUNDLE_ERROR, INVALID_OBJECT_DEFINITION

testcases = ["cluster", "host"]


@pytest.mark.parametrize('testcase', testcases)
def test_handle_unknown_words_in_bundle(client, testcase):
    with allure.step('Try to upload bundle with unknown words'):
        dir_name = 'unknown_words_in_' + testcase
        bundledir = utils.get_data_dir(__file__, dir_name)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            steps.upload_bundle(client, bundledir)
    with allure.step('Check error: Not allowed key'):
        INVALID_OBJECT_DEFINITION.equal(e, 'Not allowed key', 'in ' + testcase)


def test_shouldnt_load_same_bundle_twice(client):
    with allure.step('Try to upload same bundle twice'):
        bundledir = utils.get_data_dir(__file__, 'bundle_directory_exist')
        steps.upload_bundle(client, bundledir)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            steps.upload_bundle(client, bundledir)
    with allure.step('Check error: bundle directory already exists'):
        BUNDLE_ERROR.equal(e, 'bundle directory', 'already exists')
