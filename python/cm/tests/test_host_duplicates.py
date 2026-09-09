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

from core.cluster import ClusterService
from core.types import ActionTargetDescriptor, ADCMCoreType
from infra.services import get_config_service
from rbac.scenarios import RBACScenarios
from tests.base import BaseTestCase
from use_cases.transition.host.duplicate import create_duplicate

from cm.legacy.services.job.context import get_inventory_data
from cm.tests.dependencies import WithDishkaContainer
from cm.transition.status import StatusScenarios


class TestHostDuplicateBugs(WithDishkaContainer, BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle_root = Path(__file__).parent / "bundles"

        provider_bundle = self.uc.upload_bundle(bundle_root / "provider")

        provider = self.uc.add_provider(bundle=provider_bundle, name="pp")
        self.host = self.uc.add_host(provider=provider, fqdn="host-1")

        cluster_bundle = self.uc.upload_bundle(bundle_root / "cluster_1")

        self.cluster = self.uc.add_cluster(bundle=cluster_bundle, name="cc")

    def test_adcm_6948_prepare_inventory_with_host_duplicate_when_original_has_no_config(self):
        # imitate absense of config
        self.host.config = None
        self.host.save(update_fields=["config"])

        create_duplicate(
            host_id=self.host.pk,
            name="dup",
            cluster_id=self.cluster.pk,
            config_service=get_config_service(),
            rbac_scenarios=RBACScenarios(),
            status_scenarios=StatusScenarios(cluster_service=self.uc.container.get(ClusterService)),
        )

        target = ActionTargetDescriptor(id=self.cluster.pk, type=ADCMCoreType.CLUSTER)

        get_inventory_data(target=target, is_host_action=False, cluster_service=self.uc.container.get(ClusterService))
