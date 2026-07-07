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

from collections.abc import Iterable
from itertools import chain

from cm.models import Cluster, ClusterBind, ConcernItem, ConfigLog, Service, TaskLog, Upgrade
from tests.suites import ADCMDjangoAPISuite


class TestUpgradeWithImport(ADCMDjangoAPISuite):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        import_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "cluster_import")
        cls.import_cluster = cls.uc.add_cluster(bundle=import_bundle, name="c1")

        cls.upgrade_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "cluster_import_upgrade")

        export_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "cluster_export")
        cls.export_cluster = cls.uc.add_cluster(bundle=export_bundle, name="export")
        cls.export_service, *_ = cls.uc.add_services_to_cluster(["service_export"], cluster=cls.export_cluster)

    def to_bind(self, export) -> dict:
        return {"id": export.pk, "type": ("cluster" if isinstance(export, Cluster) else "service")}

    def import_cluster_via_api(self):
        self.import_via_api(target=self.import_cluster, exports=[self.export_cluster])
        self.assert_cluster_bind_exists()

    def import_via_api(self, target: Cluster | Service, exports: Iterable[Cluster | Service]):
        response = self.client.v2[target, "imports"].post(
            data=[{"source": bind} for bind in map(self.to_bind, exports)]
        )
        self.assertEqual(response.status_code, 201)

    def get_config(self, obj: Cluster):
        current_config_id = obj.__class__.objects.values_list("config__current", flat=True).get(id=obj.pk)
        return ConfigLog.objects.get(id=current_config_id)

    def get_before_upgrade(self, obj: Cluster):
        obj.refresh_from_db(fields=["before_upgrade"])
        return obj.before_upgrade

    def has_import_concern(self, owner: Cluster | Service) -> bool:
        return ConcernItem.objects.filter(owner_id=owner.pk, owner_type=owner.content_type).exists()

    def assert_launched_task_succeed(self):
        task_id = self.task_runner.expect_task_launched().id
        status = TaskLog.objects.values_list("status", flat=True).get(id=task_id)
        self.assertEqual(status, "success")

    def assert_cluster_bind_exists(self):
        bind = ClusterBind.objects.filter(cluster_id=self.import_cluster.pk, source_cluster_id=self.export_cluster.pk)
        self.assertTrue(bind.exists())

    def assert_imports_via_api(self, target: Cluster | Service, exports: Iterable[Cluster | Service]) -> None:
        expected_binds = list(map(self.to_bind, exports))
        response = self.client.v2[target, "imports"].get()
        self.assertEqual(response.status_code, 200)
        actual_binds = [
            bind_entry["source"]
            for bind_entry in chain.from_iterable(entry["binds"] for entry in response.json()["results"])
        ]
        # comparison may require sorting one day
        self.assertListEqual(actual_binds, expected_binds)

    def test_adcm_7888_unbind_import_after_get_upgrade(self):
        upgrade = Upgrade.objects.get(bundle=self.upgrade_bundle, name="upgrade")
        self.import_cluster_via_api()

        response = self.client.v2[self.import_cluster, "upgrades", upgrade].get()

        self.assertEqual(response.status_code, 200)
        self.assert_cluster_bind_exists()

    def test_imports_available_in_scripts_before_upgrade(self):
        expected = {
            "cluster_export": {"gfe": {"plain": "pt", "sec": "very_secret", "secmap": {"a": "vs"}}},
            "not_exist": {"group": {"string": "string"}},
        }
        upgrade = Upgrade.objects.get(bundle=self.upgrade_bundle, name="upgrade_with_template")
        self.import_cluster_via_api()

        response = self.client.v2[self.import_cluster, "upgrades", upgrade, "run"].post()

        self.assertEqual(response.status_code, 200)
        self.task_runner.run_launched_task()
        self.assert_launched_task_succeed()
        config = self.get_config(obj=self.import_cluster)
        self.assertDictEqual(config.config["debug"]["before_upgrade"]["imports"], expected)
        before_upgrade_section = self.get_before_upgrade(self.import_cluster)["imports"]["config"]["cluster_export"][
            "gfe"
        ]
        self.assertEqual(before_upgrade_section["plain"], "pt")
        self.assertTrue(before_upgrade_section["sec"]["__ansible_vault"].startswith("$ANSIBLE_VAULT;"))
        self.assertTrue(before_upgrade_section["secmap"]["a"]["__ansible_vault"].startswith("$ANSIBLE_VAULT;"))
