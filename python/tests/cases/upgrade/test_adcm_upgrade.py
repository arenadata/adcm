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


"""Behavior "freeze" of ADCM self-upgrade (switch of ADCM object to newer ADCM bundle)"""

from pathlib import Path
from typing import Final

from cm.models import ADCM, ConfigLog, ObjectType, Prototype
from use_cases.bundle import InitOrUpgradeADCM

from tests.suites import ADCMDjangoAPISuiteNoBundles

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "adcm_upgrade"


class TestADCMUpgrade(ADCMDjangoAPISuiteNoBundles):
    maxDiff = None

    def test_config_adapted_to_new_bundle(self) -> None:
        adcm = ADCM.objects.get()
        initial_prototype = adcm.prototype
        self.uc.change_config(adcm, values_diff={"global": {"adcm_url": "http://changed.url"}})

        self.container.get(InitOrUpgradeADCM).do(alternative_adcm_dir=BUNDLES_DIR / "adcm_v_next")

        adcm.refresh_from_db()
        self.assertNotEqual(adcm.prototype_id, initial_prototype.pk)  # pyright: ignore[reportAttributeAccessIssue]
        self.assertEqual(adcm.prototype, Prototype.objects.get(type=ObjectType.ADCM, version="999.0"))

        config = ConfigLog.objects.get(id=adcm.config.current)  # pyright: ignore[reportOptionalMemberAccess]
        # kept value is preserved, new one gets default, the ones absent in new bundle are dropped
        self.assertDictEqual(config.config, {"global": {"adcm_url": "http://changed.url", "added": "added-default"}})
        self.assertEqual(config.description, "upgrade")
