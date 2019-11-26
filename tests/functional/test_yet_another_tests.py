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
import os

import coreapi
import pytest

# pylint: disable=W0611, W0621
from tests.library import steps
from tests.library.errorcodes import BUNDLE_ERROR, INVALID_OBJECT_DEFINITION

BUNDLES = os.path.join(os.path.dirname(__file__), "stacks/")

testcases = [
    ("cluster"),
    ("host")
]


@pytest.mark.parametrize('testcase', testcases)
def test_handle_unknown_words_in_bundle(client, testcase):
    bundledir = os.path.join(BUNDLES, 'unknown_words_in_' + testcase + '_bundle')
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, bundledir)
    INVALID_OBJECT_DEFINITION.equal(e, 'Not allowed key', 'in ' + testcase)


def test_shouldnt_load_same_bundle_twice(client):
    bundledir = os.path.join(BUNDLES, 'bundle_directory_exist')
    steps.upload_bundle(client, bundledir)
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, bundledir)
    BUNDLE_ERROR.equal(e, 'bundle directory', 'already exists')
