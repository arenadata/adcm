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

from adcm.tests.base import BusinessLogicMixin
from django_test_migrations.contrib.unittest_case import MigratorTestCase

# ruff: noqa: N806


class TestDirectMigration(MigratorTestCase, BusinessLogicMixin):
    migrate_from = ("cm", "0136_restore_component_fks")
    migrate_to = ("cm", "0138_rename_table_groupconfig_to_confighostgroup")

    @staticmethod
    def _get_db_state(*models, state: str) -> dict:
        (
            *_,
            Cluster,
            Service,
            Component,
            HostProvider,
            Host,
            ObjectConfig,
            ConfigHostGroup,
            ContentType,
        ) = models

        m2m_chg_field = "confighostgroup_id" if state == "new_state" else "groupconfig_id"

        return {
            "cluster": tuple(Cluster.objects.values_list("id", "prototype_id")),
            "service": tuple(Service.objects.values_list("id", "cluster_id", "prototype_id")),
            "component": tuple(Component.objects.values_list("id", "cluster_id", "service_id", "prototype_id")),
            "provider": tuple(HostProvider.objects.values_list("id", "prototype_id")),
            "host": tuple(Host.objects.values_list("id", "fqdn", "cluster_id", "prototype_id").order_by("id")),
            "config_host_group_ct_id": ContentType.objects.get_for_model(ConfigHostGroup).pk,
            "config_host_groups": tuple(
                ConfigHostGroup.objects.values_list("id", "object_type", "object_id", "config").order_by("id")
            ),
            "chg_m2m": tuple(
                ConfigHostGroup.hosts.through.objects.values_list("id", "host_id", m2m_chg_field).order_by("id")
            ),
        }

    @staticmethod
    def _create_objects(*models):
        (
            Bundle,
            Prototype,
            Cluster,
            Service,
            Component,
            HostProvider,
            Host,
            ObjectConfig,
            ConfigHostGroup,
            ContentType,
        ) = models

        prototypes = {}
        for type_ in ("cluster", "service", "component", "provider", "host"):
            prototypes[type_] = Prototype.objects.create(
                bundle=Bundle.objects.create(name=f"{type_}_bundle", version="1", hash="hash"),
                type=type_,
                name=f"{type_}_prototype",
                version="1",
            )

        provider = HostProvider.objects.create(name="provider", prototype_id=prototypes["provider"].pk)
        host_0 = Host.objects.create(fqdn="host0", provider_id=provider.pk, prototype_id=prototypes["host"].pk)
        provider_chg = ConfigHostGroup.objects.create(
            object_type_id=ContentType.objects.get_for_model(HostProvider).pk,
            object_id=provider.pk,
            name="provider_chg",
            config_id=ObjectConfig.objects.create(previous=1, current=2).pk,
        )
        provider_chg.hosts.add(host_0)

        cluster = Cluster.objects.create(name="cluster", prototype_id=prototypes["cluster"].pk)
        host_1 = Host.objects.create(
            fqdn="host1", provider_id=provider.pk, prototype_id=prototypes["host"].pk, cluster_id=cluster.pk
        )
        cluster_chg = ConfigHostGroup.objects.create(
            object_type_id=ContentType.objects.get_for_model(Cluster).pk,
            object_id=cluster.pk,
            name="cluster_chg",
            config_id=ObjectConfig.objects.create(previous=1, current=2).pk,
        )
        cluster_chg.hosts.add(host_1)

        service = Service.objects.create(cluster_id=cluster.pk, prototype_id=prototypes["service"].pk)
        host_2 = Host.objects.create(
            fqdn="host2", provider_id=provider.pk, prototype_id=prototypes["host"].pk, cluster_id=cluster.pk
        )
        service_chg = ConfigHostGroup.objects.create(
            object_type_id=ContentType.objects.get_for_model(Service).pk,
            object_id=service.pk,
            name="service_chg",
            config_id=ObjectConfig.objects.create(previous=1, current=2).pk,
        )
        service_chg.hosts.add(host_2)

        component = Component.objects.create(
            cluster_id=cluster.pk, service_id=service.pk, prototype_id=prototypes["component"].pk
        )
        host_3 = Host.objects.create(
            fqdn="host3", provider_id=provider.pk, prototype_id=prototypes["host"].pk, cluster_id=cluster.pk
        )
        component_chg = ConfigHostGroup.objects.create(
            object_type_id=ContentType.objects.get_for_model(Component).pk,
            object_id=component.pk,
            name="component_chg",
            config_id=ObjectConfig.objects.create(previous=1, current=2).pk,
        )
        component_chg.hosts.add(host_3)

    def _get_models(self, state: str) -> tuple:
        self.assertIn(state, {"old_state", "new_state"})

        config_host_group_model = "GroupConfig" if state == "old_state" else "ConfigHostGroup"
        state = getattr(self, state)

        Bundle = state.apps.get_model("cm", "Bundle")
        Prototype = state.apps.get_model("cm", "Prototype")

        Cluster = state.apps.get_model("cm", "Cluster")
        Service = state.apps.get_model("cm", "Service")
        Component = state.apps.get_model("cm", "Component")

        HostProvider = state.apps.get_model("cm", "HostProvider")
        Host = state.apps.get_model("cm", "Host")

        ObjectConfig = state.apps.get_model("cm", "ObjectConfig")
        ConfigHostGroup = state.apps.get_model("cm", config_host_group_model)

        ContentType = state.apps.get_model("contenttypes", "ContentType")

        return (
            Bundle,
            Prototype,
            Cluster,
            Service,
            Component,
            HostProvider,
            Host,
            ObjectConfig,
            ConfigHostGroup,
            ContentType,
        )

    def prepare(self):
        models = self._get_models(state="old_state")
        self._create_objects(*models)
        self.db_state = self._get_db_state(*models, state="old_state")

        ContentType, ConfigHostGroup = models[-1], models[-2]
        self.assertEqual(ContentType.objects.get_for_model(ConfigHostGroup).model, "groupconfig")

    def test_migration_136_138(self):
        models = self._get_models(state="new_state")
        ContentType, ConfigHostGroup = models[-1], models[-2]

        new_state = self._get_db_state(*models, state="new_state")
        self.assertDictEqual(self.db_state, new_state)
        self.assertEqual(ContentType.objects.get_for_model(ConfigHostGroup).model, "confighostgroup")
