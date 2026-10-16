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
Behavior "freeze" of explicit `venv` of cluster objects for contract 2.1.

Components are validated with 2.0 rules, so venv introduced in 2.1 is rejected for them,
while it's accepted for services. It's a bug to be fixed later, until then it's pinned as is.
"""

from pathlib import Path
from typing import Final

from cm.errors import AdcmEx

from tests.suites import GenericTestCase

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "component_venv"


class TestExplicitVenvOfClusterObjects(GenericTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()

    def test_new_venv_on_service_success(self) -> None:
        self.uc.upload_bundle(BUNDLES_DIR / "service_with_new_venv")

    def test_new_venv_on_component_fail(self) -> None:
        with self.assertRaises(AdcmEx) as err:
            self.uc.upload_bundle(BUNDLES_DIR / "component_with_new_venv")

        self.assertEqual(err.exception.code, "BUNDLE_DEFINITION_ERROR")
        self.assertIn("Input should be '2.9' or '2.16'", err.exception.msg)
