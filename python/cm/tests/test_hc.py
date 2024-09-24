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

from adcm.tests.base import APPLICATION_JSON, BaseTestCase, BusinessLogicMixin
from rest_framework.status import HTTP_200_OK

from cm.models import Action, ServiceComponent
from cm.tests.mocks.task_runner import RunTaskMock


class TestHC(BaseTestCase, BusinessLogicMixin):
    def test_adcm_4929_run_same_hc_success(self) -> None:
        bundles_dir = Path(__file__).parent / "bundles"
        bundle = self.add_bundle(bundles_dir / "cluster_1")
        cluster = self.add_cluster(bundle=bundle, name="Cool")
        service_1 = self.add_services_to_cluster(["service_one_component"], cluster=cluster).get()
        service_2 = self.add_services_to_cluster(["service_two_components"], cluster=cluster).get()
        service_with_action = self.add_services_to_cluster(["with_hc_acl_actions"], cluster=cluster).get()

        hostprovider = self.add_provider(bundle=self.add_bundle(bundles_dir / "provider"), name="prov")
        host_1 = self.add_host(provider=hostprovider, fqdn="host-1")
        host_2 = self.add_host(provider=hostprovider, fqdn="host-2")

        self.add_host_to_cluster(cluster, host_1)
        self.add_host_to_cluster(cluster, host_2)

        component_1_1 = ServiceComponent.objects.get(service=service_1, prototype__name="component_1")
        component_2_1 = ServiceComponent.objects.get(service=service_2, prototype__name="component_1")
        component_2_2 = ServiceComponent.objects.get(service=service_2, prototype__name="component_2")
        hc = self.set_hostcomponent(
            cluster=cluster,
            entries=(
                (host_1, component_1_1),
                (host_1, component_2_1),
                (host_1, component_2_2),
                (host_2, component_2_1),
                (host_2, component_2_2),
            ),
        )
        action = Action.objects.get(prototype=service_with_action.prototype, name="with_hc")

        with RunTaskMock():
            response = self.client.post(
                path=f"/api/v2/clusters/{cluster.id}/services/{service_with_action.id}/actions/{action.id}/run/",
                data={
                    "hostComponentMap": [{"hostId": entry.host_id, "componentId": entry.component_id} for entry in hc],
                },
                content_type=APPLICATION_JSON,
            )

        # expectations changed due to existing behavior in bundles
        self.assertEqual(response.status_code, HTTP_200_OK)
