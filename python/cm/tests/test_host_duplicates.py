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

from pathlib import Path

from adcm.tests.base import BaseTestCase, BusinessLogicMixin
from core.types import ActionTargetDescriptor, ADCMCoreType

from cm.services.host.duplicates import create_duplicate
from cm.services.job.inventory._base import get_inventory_data


class TestHostDuplicateBugs(BusinessLogicMixin, BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle_root = Path(__file__).parent / "bundles"

        provider_bundle = self.add_bundle(bundle_root / "provider")

        provider = self.add_provider(bundle=provider_bundle, name="pp")
        self.host = self.add_host(provider=provider, fqdn="host-1")

        cluster_bundle = self.add_bundle(bundle_root / "cluster_1")

        self.cluster = self.add_cluster(bundle=cluster_bundle, name="cc")

    def test_adcm_6948_prepare_inventory_with_host_duplicate_when_original_has_no_config(self):
        # imitate absense of config
        self.host.config = None
        self.host.save(update_fields=["config"])

        create_duplicate(host_id=self.host.pk, name="dup", cluster_id=self.cluster.pk)

        target = ActionTargetDescriptor(id=self.cluster.pk, type=ADCMCoreType.CLUSTER)
        get_inventory_data(target=target, is_host_action=False)
