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

"""Test bundle upload"""

import allure
import pytest
from coreapi.exceptions import ErrorMessage

from tests.conftest import DUMMY_ACTION, DUMMY_CLUSTER_BUNDLE
from tests.functional.conftest import only_clean_adcm
from tests.library.errorcodes import INVALID_OBJECT_DEFINITION

ALLOW_IN_MM_ACTION = {'actions': {'some_action': {**DUMMY_ACTION, 'allow_in_maintenance_mode': True}}}


def _make_dummy_cluster_bundle(cluster_extra: dict, *services: dict):
    return [{**DUMMY_CLUSTER_BUNDLE[0], **cluster_extra}, *services]


def _make_dummy_provider_bundle(provider_extra: dict = None, host_extra: dict = None):
    provider_extra = provider_extra if provider_extra else {}
    host_extra = host_extra if host_extra else {}
    return [
        {'type': 'provider', 'version': 2.1, 'name': 'test_provider', **provider_extra},
        {'type': 'host', 'version': 2.3, 'name': 'test_host', **host_extra},
    ]


@only_clean_adcm
@pytest.mark.parametrize(
    'create_bundle_archives',
    [
        [_make_dummy_cluster_bundle(ALLOW_IN_MM_ACTION)],
        [_make_dummy_cluster_bundle({**ALLOW_IN_MM_ACTION, 'allow_maintenance_mode': False})],
        [_make_dummy_provider_bundle({'allow_maintenance_mode': False})],
        [_make_dummy_provider_bundle({}, {'allow_maintenance_mode': False})],
    ],
    ids=[
        'cluster_mm_absent_action_mm_false',
        'cluster_mm_false_action_mm_true',
        'provider_mm_false',
        'host_mm_false',
    ],
    indirect=True,
)
def test_bundle_validation_upload(sdk_client_fs, create_bundle_archives):
    """
    Test uploading bundles with invalid MM directives
    """
    with allure.step('Upload bundle and expect upload to fail'):
        bundle_path, *_ = create_bundle_archives
        with pytest.raises(ErrorMessage) as e:
            sdk_client_fs.upload_from_fs(bundle_path)
        INVALID_OBJECT_DEFINITION.equal(e)
