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
Behavior "freeze" of `allow_to_terminate` in upgrades.

Upgrade itself can't declare it, so there's nothing to propagate to its scripts.
Statically declared upgrade scripts reject it, while rendered ones (`scripts_template`) accept and respect it.
The latter is most likely unintended and may be fixed later, until then it's pinned as is.
"""

from pathlib import Path
from typing import Final

from cm.errors import AdcmEx
from cm.models import Upgrade
from cm.tests.scripts import retrieve_rich_jobs
from rest_framework.status import HTTP_200_OK
from unittest_parametrize import param, parametrize

from tests.suites import ADCMDjangoAPISuite

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "upgrade_scripts"


class TestAllowToTerminateInUpgrade(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.old_bundle = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_old")

    @parametrize(
        "bundle_name",
        [
            param("static_upgrade_with_allow_to_terminate", id="with_scripts"),
            param("rendered_upgrade_with_allow_to_terminate", id="with_scripts_template"),
        ],
    )
    def test_allow_to_terminate_on_upgrade_fail(self, bundle_name: str) -> None:
        with self.assertRaises(AdcmEx) as err:
            self.uc.upload_bundle(BUNDLES_DIR / bundle_name)

        self.assertEqual(err.exception.code, "BUNDLE_DEFINITION_ERROR")
        self.assertIn("allow_to_terminate", err.exception.msg)
        self.assertIn("Extra inputs are not permitted", err.exception.msg)

    def test_allow_to_terminate_on_static_upgrade_scripts_fail(self) -> None:
        with self.assertRaises(AdcmEx) as err:
            self.uc.upload_bundle(BUNDLES_DIR / "static_scripts_with_allow_to_terminate")

        self.assertEqual(err.exception.code, "BUNDLE_DEFINITION_ERROR")
        self.assertIn("Field allow_to_terminate is not allowed in here", err.exception.msg)

    def test_allow_to_terminate_on_rendered_upgrade_scripts_success(self) -> None:
        new_bundle = self.uc.upload_bundle(BUNDLES_DIR / "rendered_scripts_with_allow_to_terminate")
        cluster = self.uc.add_cluster(bundle=self.old_bundle, name="to upgrade")
        upgrade = Upgrade.objects.select_related("action").get(bundle=new_bundle)

        # scripts rendered from template are unknown until rendering, so nothing is stored
        self.assertIsNotNone(upgrade.action)
        self.assertIsNone(upgrade.action.scripts)

        response = self.client.v2[cluster, "upgrades", upgrade, "run"].post()

        self.assertEqual(response.status_code, HTTP_200_OK)
        terminatable = {
            job.spec.names.internal: job.spec.details.terminatable for job in retrieve_rich_jobs(response.json()["id"])
        }
        # internal scripts are never terminatable
        self.assertDictEqual(terminatable, {"run": True, "switch": False})
