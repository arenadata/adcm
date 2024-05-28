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

from hashlib import md5
from operator import itemgetter
from pathlib import Path

from adcm.tests.base import BaseTestCase, BusinessLogicMixin
from django.utils import timezone

from cm.collect_statistics.collectors import CommunityBundleCollector
from cm.models import Bundle


class TestBundle(BaseTestCase, BusinessLogicMixin):
    def setUp(self) -> None:
        super().setUp()

        self.bundles_dir = Path(__file__).parent / "bundles"
        self.maxDiff = None

    def test_collect_community_bundle_collector(self) -> None:
        # prepare data
        bundle_cluster_reg = self.add_bundle(self.bundles_dir / "cluster_1")
        bundle_cluster_full = self.add_bundle(self.bundles_dir / "cluster_full_config")
        bundle_prov_reg = self.add_bundle(self.bundles_dir / "provider")
        bundle_prov_full = self.add_bundle(self.bundles_dir / "provider_full_config")

        cluster_reg_1 = self.add_cluster(bundle=bundle_cluster_reg, name="Regular 1")
        cluster_full = self.add_cluster(bundle=bundle_cluster_full, name="Full 1")
        cluster_reg_2 = self.add_cluster(bundle=bundle_cluster_reg, name="Regular 2")

        provider_full_1 = self.add_provider(bundle=bundle_prov_full, name="Prov Full 1")
        provider_full_2 = self.add_provider(bundle=bundle_prov_full, name="Prov Full 2")
        provider_reg_1 = self.add_provider(bundle=bundle_prov_reg, name="Prov Reg 1")

        host_1 = self.add_host(provider=provider_full_1, fqdn="host-1", cluster=cluster_reg_1)
        host_2 = self.add_host(provider=provider_full_1, fqdn="host-2", cluster=cluster_reg_2)
        self.add_host(provider=provider_reg_1, fqdn="host-3", cluster=cluster_reg_1)

        self.add_services_to_cluster(["service_one_component"], cluster=cluster_reg_1)
        service_2 = self.add_services_to_cluster(["service_two_components"], cluster=cluster_reg_1).get()
        service_3 = self.add_services_to_cluster(["service_two_components"], cluster=cluster_reg_2).get()

        component_1, component_2 = service_2.servicecomponent_set.order_by("id").all()
        component_3 = service_3.servicecomponent_set.order_by("id").first()
        self.set_hostcomponent(cluster=cluster_reg_1, entries=((host_1, component_1), (host_1, component_2)))

        self.set_hostcomponent(cluster=cluster_reg_2, entries=((host_2, component_3),))

        # prepare expected
        order_hc_by = itemgetter("component_name")
        by_name = itemgetter("name")
        collect = CommunityBundleCollector(date_format="%Y")
        current_year = str(timezone.now().year)
        host_1_name_hash = md5(host_1.fqdn.encode("utf-8")).hexdigest()  # noqa: S324
        host_2_name_hash = md5(host_2.fqdn.encode("utf-8")).hexdigest()  # noqa: S324
        expected_bundles = [
            {"name": bundle.name, "version": bundle.version, "edition": "community", "date": current_year}
            for bundle in (
                bundle_cluster_reg,
                bundle_cluster_full,
                bundle_prov_reg,
                bundle_prov_full,
                Bundle.objects.get(name="ADCM"),
            )
        ]
        expected = {
            "bundles": sorted(expected_bundles, key=by_name),
            "providers": sorted(
                [
                    {"name": provider_full_1.name, "bundle": expected_bundles[3], "host_count": 2},
                    {"name": provider_full_2.name, "bundle": expected_bundles[3], "host_count": 0},
                    {"name": provider_reg_1.name, "bundle": expected_bundles[2], "host_count": 1},
                ],
                key=by_name,
            ),
            "clusters": sorted(
                [
                    {
                        "name": cluster_full.name,
                        "host_count": 0,
                        "bundle": expected_bundles[1],
                        "host_component_map": [],
                    },
                    {
                        "name": cluster_reg_1.name,
                        "host_count": 2,
                        "bundle": expected_bundles[0],
                        "host_component_map": sorted(
                            [
                                {
                                    "host_name": host_1_name_hash,
                                    "component_name": component_1.name,
                                    "service_name": service_2.name,
                                },
                                {
                                    "host_name": host_1_name_hash,
                                    "component_name": component_2.name,
                                    "service_name": service_2.name,
                                },
                            ],
                            key=order_hc_by,
                        ),
                    },
                    {
                        "name": cluster_reg_2.name,
                        "host_count": 1,
                        "bundle": expected_bundles[0],
                        "host_component_map": [
                            {
                                "host_name": host_2_name_hash,
                                "component_name": component_3.name,
                                "service_name": service_3.name,
                            },
                        ],
                    },
                ],
                key=by_name,
            ),
        }

        # check
        actual = collect().model_dump()

        # order for reproducible comparison
        for root_key in actual:
            actual[root_key] = sorted(actual[root_key], key=by_name)

        for entry in actual["clusters"]:
            entry["host_component_map"] = sorted(entry["host_component_map"], key=order_hc_by)

        self.assertDictEqual(actual, expected)
