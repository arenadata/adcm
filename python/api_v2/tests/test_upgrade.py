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

from unittest.mock import patch

from api_v2.tests.base import BaseAPITestCase
from cm.models import Upgrade
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK


class TestUpgrade(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        cluster_bundle_1_upgrade_path = (
            settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_one_upgrade"
        )
        bundle_upgrade = self.add_bundle(source_dir=cluster_bundle_1_upgrade_path)

        self.upgrade = Upgrade.objects.get(
            name="upgrade",
            bundle=bundle_upgrade,
        )
        self.upgrade_via_action = Upgrade.objects.get(name="upgrade_via_action", bundle=bundle_upgrade)

    def test_list_upgrades_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:upgrade-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:upgrade-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.upgrade.pk}),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_run_success(self):
        with patch("api_v2.upgrade.views.do_upgrade"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:upgrade-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.upgrade_via_action.pk},
                ),
                data={
                    "host_component_map": [{}],
                    "config": {},
                    "attr": {},
                    "is_verbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
