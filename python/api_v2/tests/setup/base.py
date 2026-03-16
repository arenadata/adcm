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


from adcm.tests.base import WithPreparedFSAndInitADCM
from adcm.tests.client import ADCMTestClient
import django.test

from api_v2.tests.base import TEST_BUNDLES_DIR, TEST_FILES_DIR
from api_v2.tests.setup.overrides import (
    get_task_runner_manager,
)


class BaseAPITestCase(django.test.TestCase, WithPreparedFSAndInitADCM):
    """
    Obligatory part of any API v2 based test
    """

    # is required for correct type detection in test cases
    client: ADCMTestClient  # pyright: ignore[reportIncompatibleVariableOverride]
    client_class = ADCMTestClient

    @classmethod
    def setUpClass(cls):
        # important init for django is happening here
        super().setUpClass()

        # task runner "patch"
        cls.task_runner = get_task_runner_manager()

        # ADCM setup is copied from previous base.py

        cls.test_bundles_dir = TEST_BUNDLES_DIR
        cls.test_files_dir = TEST_FILES_DIR

    def setUp(self) -> None:
        super().setUp()

        # precaution to avoid getting launched task from previous test
        # YET it's still possible to get falsely "launched" with 200-ok -> 409 sort of combos
        # or 200 -> 200 gettings previously launched (thou unlikely)
        self.task_runner.reset()

        self.client.login(username="admin", password="admin")
