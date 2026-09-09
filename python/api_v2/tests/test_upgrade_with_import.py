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

from collections.abc import Callable, Iterable
from functools import partial
from itertools import chain

from cm.models import Action, Cluster, ClusterBind, ConcernItem, ConfigLog, PrototypeImport, Service, TaskLog, Upgrade
from rest_framework.status import HTTP_204_NO_CONTENT
from tests.suites import ADCMDjangoAPISuite
from unittest_parametrize import param, parametrize


class TestUpgradeWithImport(ADCMDjangoAPISuite):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cls.import_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "cluster_import")
        cls.import_cluster = cls.uc.add_cluster(bundle=cls.import_bundle, name="c1")

        cls.upgrade_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "cluster_import_upgrade")

        cls.export_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "cluster_export")
        cls.export_cluster = cls.uc.add_cluster(bundle=cls.export_bundle, name="export")
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

    def get_bind_ids_dict(self, obj: Cluster | Service, prefix: str = "") -> dict:
        if isinstance(obj, Cluster):
            cluster_id = obj.pk
            service_id = None
        else:
            cluster_id = obj.cluster_id
            service_id = obj.pk

        return {f"{prefix}cluster_id": cluster_id, f"{prefix}service_id": service_id}

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

        self.assertCountEqual(actual_binds, expected_binds)

    def assert_bu_binds(self, target: Cluster | Service, sources: Iterable[Cluster | Service]) -> None:
        target_ids = self.get_bind_ids_dict(obj=target)
        expected_binds = [{**target_ids, **self.get_bind_ids_dict(obj=s, prefix="source_")} for s in sources]

        self.assertCountEqual(self.get_before_upgrade(target)["binds"], expected_binds)

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

    @parametrize(
        argnames=("make_old_binds_incompatible", "expected_imports", "expected_concerns"),
        argvalues=[
            param(  # Happy path
                False,
                {"cluster": ["export_cluster", "export_service"], "service": ["export_service"]},
                {"cluster": None, "service": None},
            ),
            param(  # Make export_service incompatible by version
                True,
                {"cluster": ["export_cluster"], "service": []},
                {"cluster": "import_issue", "service": "import_issue"},
            ),
        ],
        ids=("happy_path", "incompatible_by_version"),
    )
    def test_adcm_7982_restore_binds_on_revert_upgrade(
        self, make_old_binds_incompatible: bool, expected_imports: dict, expected_concerns: dict
    ):
        service_with_required_import = self.uc.add_services_to_cluster(
            names=["staying_alive"], cluster=self.import_cluster
        )[0]
        expected_binds = [
            partial(
                self.assert_bu_binds, target=self.import_cluster, sources=[self.export_cluster, self.export_service]
            ),
            partial(self.assert_bu_binds, target=service_with_required_import, sources=[self.export_service]),
        ]
        self._adcm_7982_set_imports_and_upgrade(modify_imports_get_assert_funcs=lambda: expected_binds)

        if make_old_binds_incompatible:
            self.export_service.prototype.version = "999"
            self.export_service.prototype.save(update_fields=["version"])

        # revert
        expected_imports = {
            "cluster": [getattr(self, name) for name in expected_imports["cluster"]],
            "service": [getattr(self, name) for name in expected_imports["service"]],
        }

        self._adcm_7982_revert_upgrade_assert_proto_version_and_before_upgrade()

        self.assert_imports_via_api(target=self.import_cluster, exports=expected_imports["cluster"])
        self.assert_imports_via_api(target=service_with_required_import, exports=expected_imports["service"])

        if expected_concerns["cluster"]:
            self.assertEqual(self.import_cluster.concerns.get().name, expected_concerns["cluster"])
        else:
            self.assertEqual(self.import_cluster.concerns.count(), 0)
        if expected_concerns["service"]:
            self.assertEqual(service_with_required_import.concerns.get().name, expected_concerns["cluster"])
        else:
            self.assertEqual(service_with_required_import.concerns.count(), 0)

    def test_adcm_7982_restore_binds_after_deleted_source(self):
        service_with_required_import = self.uc.add_services_to_cluster(
            names=["staying_alive"], cluster=self.import_cluster
        )[0]
        expected_binds = [
            partial(
                self.assert_bu_binds, target=self.import_cluster, sources=[self.export_cluster, self.export_service]
            ),
            partial(self.assert_bu_binds, target=service_with_required_import, sources=[self.export_service]),
        ]
        self._adcm_7982_set_imports_and_upgrade(modify_imports_get_assert_funcs=lambda: expected_binds)

        # delete export_cluster with export_service
        response = self.client.v2[self.export_cluster].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        # revert
        self._adcm_7982_revert_upgrade_assert_proto_version_and_before_upgrade()

        # expect no imports and 1 import concern
        self.assert_imports_via_api(target=self.import_cluster, exports=[])
        self.assert_imports_via_api(target=service_with_required_import, exports=[])

        self.assertEqual(self.import_cluster.concerns.get().name, "import_issue")
        self.assertEqual(service_with_required_import.concerns.get().name, "import_issue")

    @parametrize(
        argnames=("delete_second_export_service",),
        argvalues=[param(False), param(True)],
        ids=("restore_all_multibinds", "partial_restore_due_to_obj_deletion"),
    )
    def test_adcm_7982_restore_multibinds(self, delete_second_export_service: bool):
        service_with_required_import = self.uc.add_services_to_cluster(
            names=["staying_alive"], cluster=self.import_cluster
        )[0]
        self._adcm_7982_set_imports_and_upgrade(
            modify_imports_get_assert_funcs=self._adcm_7982_create_second_export_objects_set_multibinds
        )

        # retrieve second export objects
        second_export_cluster = Cluster.objects.get(name="second_export_cluster")
        second_export_service = Service.objects.get(cluster=second_export_cluster, prototype__name="service_export")

        if delete_second_export_service:
            response = self.client.v2[second_export_service].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        # revert
        self._adcm_7982_revert_upgrade_assert_proto_version_and_before_upgrade()

        # expect multibinds restored
        expected_sources_cluster = [self.export_cluster, self.export_service, second_export_cluster]
        expected_sources_service = [self.export_service]
        if not delete_second_export_service:
            expected_sources_cluster.append(second_export_service)
            expected_sources_service.append(second_export_service)

        self.assert_imports_via_api(target=self.import_cluster, exports=expected_sources_cluster)
        self.assert_imports_via_api(target=service_with_required_import, exports=expected_sources_service)

        # no concerns
        self.assertEqual(self.import_cluster.concerns.count(), 0)
        self.assertEqual(service_with_required_import.concerns.count(), 0)

    def _adcm_7982_set_imports_and_upgrade(self, modify_imports_get_assert_funcs: Callable[[], list[Callable]]):
        # get objects, set imports
        service_with_required_import = Service.objects.get(cluster=self.import_cluster, prototype__name="staying_alive")
        self.import_via_api(target=self.import_cluster, exports=[self.export_cluster, self.export_service])
        self.import_via_api(target=service_with_required_import, exports=[self.export_service])

        self.assertEqual(self.import_cluster.prototype.version, "1.0")
        self.assertEqual(self.get_before_upgrade(self.import_cluster), {"state": None})
        self.assertEqual(self.get_before_upgrade(service_with_required_import), {"state": None})

        assert_binds = modify_imports_get_assert_funcs()

        # upgrade
        upgrade = Upgrade.objects.get(bundle=self.upgrade_bundle, name="upgrade")
        response = self.client.v2[self.import_cluster, "upgrades", upgrade, "run"].post()
        self.assertEqual(response.status_code, 204)

        self.import_cluster.refresh_from_db(fields=["prototype"])
        self.assertEqual(self.import_cluster.prototype.version, "2.0")
        for assert_func in assert_binds:
            assert_func()
        self.assert_imports_via_api(target=self.import_cluster, exports=[])
        self.assert_imports_via_api(target=service_with_required_import, exports=[])

    def _adcm_7982_revert_upgrade_assert_proto_version_and_before_upgrade(self):
        service_with_required_import = Service.objects.get(cluster=self.import_cluster, prototype__name="staying_alive")

        revert_action = Action.objects.get(prototype=self.import_cluster.prototype, name="revert")
        response = self.client.v2[self.import_cluster, "actions", revert_action, "run"].post()
        self.assertEqual(response.status_code, 200)
        self.task_runner.run_launched_task()

        self.import_cluster.refresh_from_db(fields=["prototype"])
        self.assertEqual(self.import_cluster.prototype.version, "1.0")
        self.assertEqual(self.get_before_upgrade(self.import_cluster), {"state": None})
        self.assertEqual(self.get_before_upgrade(service_with_required_import), {"state": None})

    def _adcm_7982_create_second_export_objects_set_multibinds(self):
        service_with_required_import = Service.objects.get(cluster=self.import_cluster, prototype__name="staying_alive")

        # modify imports: multibind=True
        PrototypeImport.objects.filter(prototype=self.import_cluster.prototype).update(multibind=True)
        PrototypeImport.objects.filter(prototype=service_with_required_import.prototype).update(multibind=True)

        # make second export cluster
        second_export_cluster = self.uc.add_cluster(bundle=self.export_bundle, name="second_export_cluster")
        second_export_service, *_ = self.uc.add_services_to_cluster(["service_export"], cluster=second_export_cluster)

        self.import_via_api(
            target=self.import_cluster,
            exports=[self.export_cluster, self.export_service, second_export_cluster, second_export_service],
        )
        self.import_via_api(target=service_with_required_import, exports=[self.export_service, second_export_service])

        self.assert_imports_via_api(
            target=self.import_cluster,
            exports=[self.export_cluster, self.export_service, second_export_cluster, second_export_service],
        )
        self.assert_imports_via_api(
            target=service_with_required_import, exports=[self.export_service, second_export_service]
        )

        return [
            partial(
                self.assert_bu_binds,
                target=self.import_cluster,
                sources=[self.export_cluster, self.export_service, second_export_cluster, second_export_service],
            ),
            partial(
                self.assert_bu_binds,
                target=service_with_required_import,
                sources=[self.export_service, second_export_service],
            ),
        ]

    def test_adcm_8319_upgrade_cl_to_new_v_without_service_with_import(self):
        upgrade = Upgrade.objects.get(bundle=self.upgrade_bundle, name="upgrade")

        self.import_cluster_via_api()
        service, *_ = self.uc.add_services_to_cluster(
            ["service_import_removed_after_upgrade"], cluster=self.import_cluster
        )
        self.import_via_api(target=service, exports=[self.export_cluster])
        service_bind = ClusterBind.objects.get(
            cluster=self.import_cluster,
            service=service,
            source_cluster=self.export_cluster,
        )

        check_service_bind_exists = ClusterBind.objects.filter(id=service_bind.id).exists

        self.assertTrue(check_service_bind_exists())

        response = self.client.v2[self.import_cluster, "upgrades", upgrade, "run"].post()

        self.assertEqual(response.status_code, 204)
        self.task_runner.expect_task_not_launched()
        self.assertFalse(check_service_bind_exists())
        self.assertFalse(Service.objects.filter(id=service.id).exists())
