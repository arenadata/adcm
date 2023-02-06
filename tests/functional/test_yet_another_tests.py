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

"""Uncategorized tests"""

import allure
import coreapi
import pytest
from adcm_client.packer.bundle_build import build
from adcm_pytest_plugin import utils
from tests.library.errorcodes import BUNDLE_ERROR, INVALID_OBJECT_DEFINITION

testcases = ["cluster", "host"]


@pytest.mark.parametrize("testcase", testcases)
def test_handle_unknown_words_in_bundle(sdk_client_fs, testcase):
    """Test bundle with unspecified words should not be uploaded"""
    with allure.step("Try to upload bundle with unknown words"):
        dir_name = "unknown_words_in_" + testcase
        bundledir = utils.get_data_dir(__file__, dir_name)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            sdk_client_fs.upload_from_fs(bundledir)
    with allure.step("Check error: Not allowed key"):
        INVALID_OBJECT_DEFINITION.equal(e, 'Map key "confi" is not allowed here')


def test_shouldnt_load_same_bundle_twice(sdk_client_fs):
    """Test bundle should not be uploaded twice"""
    with allure.step("Build bundle"):
        bundledir = utils.get_data_dir(__file__, "bundle_directory_exist")
        for path, steram in build(repopath=bundledir).items():
            with open(path, "wb") as file:
                file.write(steram.read())
                bundle_tar_path = path
    with allure.step("Try to upload same bundle twice"):
        sdk_client_fs.upload_from_fs(bundle_tar_path)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            sdk_client_fs.upload_from_fs(bundle_tar_path)
    with allure.step("Check error: bundle directory already exists"):
        BUNDLE_ERROR.equal(e, "already exists")
