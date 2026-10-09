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

"""G1: non-RBAC triggers of the RBAC write side, topology changes"""

from rest_framework.status import HTTP_201_CREATED

from tests.cases.rbac.setup import RBACWriteSideSuite


class TestG1Topology(RBACWriteSideSuite):
    def test_g1_01_create_host_free(self) -> None:
        with self.act():
            response = (self.client.v2 / "hosts").post(
                data={"hostproviderId": self.provider_p1.pk, "name": "g1-01-free"}
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_01_create_host_in_cluster(self) -> None:
        with self.act():
            response = (self.client.v2 / "hosts").post(
                data={
                    "hostproviderId": self.provider_p1.pk,
                    "name": "g1-01-in-cluster",
                    "clusterId": self.cluster_a1.pk,
                }
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)
