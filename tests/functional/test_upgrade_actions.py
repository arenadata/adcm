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

"""
Test "scripts" section of bundle's "upgrade" section
"""

import os

import allure
import pytest
from adcm_pytest_plugin.utils import get_data_dir, catch_failed, parametrize_by_data_subdirs
from coreapi.exceptions import ErrorMessage

from tests.library.errorcodes import INVALID_UPGRADE_DEFINITION, INVALID_OBJECT_DEFINITION


@parametrize_by_data_subdirs(__file__, 'validation', 'valid')
def test_validation_succeed_on_upload(sdk_client_fs, path):
    """Test that valid bundles with upgrade actions succeed to upload"""
    verbose_bundle_name = os.path.basename(path).replace('_', ' ').capitalize()
    with allure.step(f'Upload bundle "{verbose_bundle_name}" and expect it to succeed'), catch_failed(
        ErrorMessage, f'Bundle "{verbose_bundle_name}" should be uploaded successfully'
    ):
        bundle = sdk_client_fs.upload_from_fs(path)
        bundle.delete()


@pytest.mark.parametrize(
    ('bundle_dir_name', 'expected_error'),
    [
        ('bundle_switch_in_regular_actions', INVALID_OBJECT_DEFINITION),
        ('incorrect_internal_action', INVALID_UPGRADE_DEFINITION),
        ('no_bundle_switch', INVALID_UPGRADE_DEFINITION),
    ],
)
def test_validation_failed_on_upload(bundle_dir_name, expected_error, sdk_client_fs):
    """Test that invalid bundles with upgrade actions fails to upload"""

    verbose_bundle_name = bundle_dir_name.replace('_', ' ').capitalize()
    invalid_bundle_file = get_data_dir(__file__, 'validation', 'invalid', bundle_dir_name)
    with allure.step(f'Upload bundle "{verbose_bundle_name}" and expect upload to fail'):
        with pytest.raises(ErrorMessage) as e:
            sdk_client_fs.upload_from_fs(invalid_bundle_file)
        expected_error.equal(e)
