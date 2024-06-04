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

from rest_framework.status import HTTP_200_OK

from api_v2.tests.base import BaseAPITestCase

CONFIG_SCHEMA = "config-schema"


class TestConfigBugs(BaseAPITestCase):
    def test_cluster_variant_bug_adcm_4778(self):
        # problem is with absent service
        bundle = self.add_bundle(self.test_bundles_dir / "bugs" / "ADCM-4778")
        cluster = self.add_cluster(bundle, "cooler")

        response = self.client.v2[cluster, CONFIG_SCHEMA].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
