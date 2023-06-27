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


from api_v2.tests.base import BaseAPITestCase
from cm.models import Upgrade
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT


class TestUpgrade(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        cluster_bundle_1_upgrade_path = (
            settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_one_upgrade"
        )
        provider_bundle_upgrade_path = (
            settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "provider_upgrade"
        )
        cluster_bundle_upgrade = self.add_bundle(source_dir=cluster_bundle_1_upgrade_path)
        provider_bundle_upgrade = self.add_bundle(source_dir=provider_bundle_upgrade_path)

        self.cluster_upgrade = Upgrade.objects.get(
            name="upgrade",
            bundle=cluster_bundle_upgrade,
        )
        self.provider_upgrade = Upgrade.objects.get(
            name="upgrade",
            bundle=provider_bundle_upgrade,
        )
        self.upgrade_cluster_via_action = Upgrade.objects.get(name="upgrade_via_action", bundle=cluster_bundle_upgrade)
        self.upgrade_host_via_action = Upgrade.objects.get(name="upgrade_via_action", bundle=provider_bundle_upgrade)

    def test_cluster_list_upgrades_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:upgrade-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_cluster_upgrade_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_upgrade.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_cluster_upgrade_run_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.upgrade_cluster_via_action.pk},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_provider_list_upgrades_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:upgrade-list", kwargs={"hostprovider_pk": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_provider_upgrade_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_upgrade.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_provider_upgrade_run_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.upgrade_host_via_action.pk},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_provider_upgrade_run_violate_constraint_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.cluster_upgrade.pk},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_cluster_upgrade_run_violate_constraint_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.provider_upgrade.pk},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_provider_upgrade_run_not_found_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_upgrade.pk + 10},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_run_not_found_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_upgrade.pk + 10},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_retrieve_not_found_fail(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_upgrade.pk + 10},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_hostprovider_upgrade_retrieve_not_found_fail(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.cluster_upgrade.pk + 10},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
