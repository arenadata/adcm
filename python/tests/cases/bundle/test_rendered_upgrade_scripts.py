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
`allow_to_terminate` is supported by upgrades now.

It may be declared on the upgrade itself (propagated to its scripts) or on a script directly,
for both statically declared and template-rendered scripts. Internal scripts stay non-terminatable.
"""

from pathlib import Path
from typing import Final

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
            param("static_upgrade_with_allow_to_terminate", id="static_upgrade"),
            param("rendered_upgrade_with_allow_to_terminate", id="rendered_upgrade"),
            param("static_scripts_with_allow_to_terminate", id="static_scripts"),
            param("rendered_scripts_with_allow_to_terminate", id="rendered_scripts"),
        ],
    )
    def test_allow_to_terminate_on_upgrade_success(self, bundle_name: str) -> None:
        new_bundle = self.uc.upload_bundle(BUNDLES_DIR / bundle_name)
        cluster = self.uc.add_cluster(bundle=self.old_bundle, name="to upgrade")
        upgrade = Upgrade.objects.select_related("action").get(bundle=new_bundle)

        response = self.client.v2[cluster, "upgrades", upgrade, "run"].post()

        self.assertEqual(response.status_code, HTTP_200_OK)
        terminatable = {
            job.spec.names.internal: job.spec.details.terminatable for job in retrieve_rich_jobs(response.json()["id"])
        }
        # internal scripts are never terminatable, regular ones are
        self.assertDictEqual(terminatable, {"run": True, "switch": False})
