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

import json

from cm.models import Action
from infra.services import get_config_service, get_wizard_service
from rest_framework.status import HTTP_200_OK

from api_v2.tests.base import TEST_BUNDLES_DIR, APIV2Mixin, BaseAPITestCase
from api_v2.utils.di import prepare_container


class TestConfigTemplateContext(APIV2Mixin, BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        prepare_container.cache_clear()
        get_config_service.cache_clear()
        get_wizard_service.cache_clear()

        self.cluster_bundle = self.create_bundle(TEST_BUNDLES_DIR / "config_template_context")
        self.cluster = self.create_cluster(bundle=self.cluster_bundle, name="aaa")

        self.host = self.create_host(provider=self.provider, name="wow", cluster=self.cluster)

    def test_has_target_group(self):
        host_2 = self.create_host(provider=self.provider, name="aaaa", cluster=self.cluster)
        action_host_group = self.create_action_host_group(owner=self.cluster, name="ooo", hosts=(self.host, host_2))
        host_action = Action.objects.get(name="host_action_xxx")
        ahg_action = Action.objects.get(name="action_host_group_xxx")
        host_endpoint = self.client.v2[self.cluster, "hosts", self.host, "actions", host_action]
        ahg_endpoint = self.client.v2[action_host_group, "actions", ahg_action]

        cases = (
            ("host action", host_endpoint, [self.host.fqdn]),
            ("action host group", ahg_endpoint, [host_2.fqdn, self.host.fqdn]),
        )

        for case_name, endpoint, expected_hosts in cases:
            with self.subTest(case_name):
                response = endpoint.get()

                self.assertEqual(response.status_code, HTTP_200_OK)
                data = response.json()
                groups = json.loads(data["configuration"]["config"]["groups_in_context"])
                self.assertIn("target", groups)
                self.assertListEqual(groups["target"], expected_hosts)
