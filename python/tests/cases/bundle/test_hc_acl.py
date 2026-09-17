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
Behavior "freeze" of `hc_acl` declaration requirements on bundle upload.

`"hc_apply" requires "hc_acl"` distinguishes absent `hc_acl` from an empty one,
while stored actions always get a list.
"""

from pathlib import Path
from typing import Final, Literal, TypeAlias

from cm.errors import AdcmEx
from cm.models import Action, Upgrade
from unittest_parametrize import ParametrizedTestCase, param, parametrize

from tests.suites import GenericTestCase

Owner: TypeAlias = Literal["cluster", "service", "component"]

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "hc_acl"

OWNERS: Final[tuple[Owner, ...]] = ("cluster", "service", "component")

HC_ACL: Final = [{"service": "service", "component": "component", "action": "add"}]
# actions of `declared` bundle, the same set is defined for every owner
EXPECTED_STORED_HC_ACL: Final = {
    "hc_apply_with_empty_hc_acl": [],
    "hc_apply_with_hc_acl": HC_ACL,
    "hc_apply_in_wizard_without_hc_acl": [],
    "no_hc_apply_without_hc_acl": [],
    "no_hc_apply_with_hc_acl": HC_ACL,
}


class TestHcAclDeclaration(ParametrizedTestCase, GenericTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()

    @parametrize("owner", [param(owner, id=owner) for owner in OWNERS])
    def test_hc_apply_without_hc_acl_fail(self, owner: Owner) -> None:
        with self.assertRaises(AdcmEx) as err:
            self.uc.upload_bundle(BUNDLES_DIR / f"hc_apply_without_hc_acl_{owner}")

        self.assertEqual(err.exception.code, "BUNDLE_DEFINITION_ERROR")
        self.assertIn('"hc_apply" requires "hc_acl" declaration', err.exception.msg)

    def test_hc_acl_declaration_success(self) -> None:
        bundle = self.uc.upload_bundle(BUNDLES_DIR / "declared")

        stored = {
            (owner, name): hc_acl
            for owner, name, hc_acl in Action.objects.filter(
                prototype__bundle=bundle, name__in=EXPECTED_STORED_HC_ACL
            ).values_list("prototype__type", "name", "hostcomponentmap")
        }
        expected = {(owner, name): hc_acl for owner in OWNERS for name, hc_acl in EXPECTED_STORED_HC_ACL.items()}
        self.assertDictEqual(stored, expected)

        # upgrades can't declare `hc_acl` at all
        upgrade = Upgrade.objects.select_related("action").get(bundle=bundle, name="hc_acl_upgrade")
        self.assertIsNotNone(upgrade.action)
        self.assertEqual(upgrade.action.hostcomponentmap, [])
        # statically declared scripts are stored as plan
        self.assertIsNotNone(upgrade.action.scripts)
