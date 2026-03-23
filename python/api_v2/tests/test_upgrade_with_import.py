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

from cm.models import ClusterBind, Upgrade
from tests.suites import ADCMDjangoAPISuite


class TestUpgradeWithImport(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        import_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_import")
        self.import_cluster = self.add_cluster(bundle=import_bundle, name="c1")

        self.upgrade_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_import_upgrade")

        export_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_export")
        self.export_cluster = self.add_cluster(bundle=export_bundle, name="export")

    def test_adcm_7888_unbind_import_after_get_upgrade(self):
        response = self.client.v2[self.import_cluster, "imports"].post(
            data=[
                {"source": {"id": self.export_cluster.pk, "type": "cluster"}},
            ],
        )

        self.assertEqual(response.status_code, 201)

        bind = ClusterBind.objects.first()
        self.assertIsNotNone(bind)
        self.assertEqual(bind.cluster_id, self.import_cluster.id)
        self.assertEqual(bind.source_cluster_id, self.export_cluster.id)

        upgrade = Upgrade.objects.filter(bundle=self.upgrade_bundle).first()

        response = self.client.v2[self.import_cluster, "upgrades", upgrade].get()

        self.assertEqual(response.status_code, 200)

        bind = ClusterBind.objects.first()
        self.assertIsNotNone(bind)
