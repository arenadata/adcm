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

from adcm.tests.ansible import ADCMAnsiblePluginTestMixin
from adcm.tests.base import BusinessLogicMixin, ParallelReadyTestCase, TaskTestMixin, TestCaseWithCommonSetUpTearDown


class BaseTestEffectsOfADCMAnsiblePlugins(
    TestCaseWithCommonSetUpTearDown,
    ParallelReadyTestCase,
    BusinessLogicMixin,
    ADCMAnsiblePluginTestMixin,
    TaskTestMixin,
):
    def setUp(self) -> None:
        super().setUp()

        self.bundles_dir = Path(__file__).parent / "bundles"

        self.cluster_bundle = self.add_bundle(self.bundles_dir / "cluster")
        self.provider_bundle = self.add_bundle(self.bundles_dir / "provider")

        self.cluster = self.add_cluster(bundle=self.cluster_bundle, name="Just Cluster")

        self.provider = self.add_provider(bundle=self.provider_bundle, name="Just HP")
        self.host_1 = self.add_host(provider=self.provider, fqdn="host-1")
        self.host_2 = self.add_host(provider=self.provider, fqdn="host-2")
