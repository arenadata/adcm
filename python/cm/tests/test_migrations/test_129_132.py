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

from django_test_migrations.contrib.unittest_case import MigratorTestCase

# ruff: noqa: N806


class TestDirectMigration(MigratorTestCase):
    migrate_from = ("cm", "0129_auto_20240904_1045")
    migrate_to = ("cm", "0132_restore_FKs_after_models_renaming")

    @staticmethod
    def _get_db_state(*models, state: str) -> dict:
        (
            *_,
            Cluster,
            ServiceModel,
            ComponentModel,
            ClusterBind,
            HostComponent,
            ProviderModel,
            Host,
            ObjectConfig,
            ConfigHostGroupModel,
            AnsibleConfig,
            ActionHostGroup,
            TaskLog,
            ConcernItem,
            ContentType,
        ) = models

        m2m_chg_field = "confighostgroup_id" if state == "new_state" else "groupconfig_id"

        return {
            "service_ct_id": ContentType.objects.get_for_model(ServiceModel).pk,
            "component_ct_id": ContentType.objects.get_for_model(ComponentModel).pk,
            "provider_ct_id": ContentType.objects.get_for_model(ProviderModel).pk,
            "config_host_group_ct_id": ContentType.objects.get_for_model(ConfigHostGroupModel).pk,
            "cluster": tuple(Cluster.objects.values_list("id", "prototype_id").order_by("id")),
            "service": tuple(ServiceModel.objects.values_list("id", "cluster_id", "prototype_id").order_by("id")),
            "component": tuple(
                ComponentModel.objects.values_list("id", "cluster_id", "service_id", "prototype_id").order_by("id")
            ),
            "provider": tuple(ProviderModel.objects.values_list("id", "prototype_id").order_by("id")),
            "host": tuple(Host.objects.values_list("id", "cluster_id", "prototype_id").order_by("id")),
            "host_component": tuple(
                HostComponent.objects.values_list("id", "cluster_id", "host_id", "service_id", "component_id").order_by(
                    "id"
                )
            ),
            "cluster_bind": tuple(
                ClusterBind.objects.values_list(
                    "id", "cluster_id", "service_id", "source_cluster_id", "source_service_id"
                ).order_by("id")
            ),
            "ansible_config": tuple(
                AnsibleConfig.objects.values_list("id", "object_id", "object_type_id").order_by("id")
            ),
            "action_host_group": tuple(
                ActionHostGroup.objects.values_list("id", "object_id", "object_type_id").order_by("id")
            ),
            "config_host_group": tuple(
                ConfigHostGroupModel.objects.values_list("id", "object_id", "object_type_id").order_by("id")
            ),
            "chg_m2m": tuple(
                ConfigHostGroupModel.hosts.through.objects.values_list("id", "host_id", m2m_chg_field).order_by("id")
            ),
            "task_log": tuple(TaskLog.objects.values_list("id", "object_id", "object_type_id").order_by("id")),
            "concern_item": tuple(ConcernItem.objects.values_list("id", "owner_id", "owner_type_id").order_by("id")),
        }

    @staticmethod
    def _create_objects(*models):
        (
            Bundle,
            Prototype,
            Cluster,
            ServiceModel,
            ComponentModel,
            ClusterBind,
            HostComponent,
            ProviderModel,
            Host,
            ObjectConfig,
            ConfigHostGroupModel,
            AnsibleConfig,
            ActionHostGroup,
            TaskLog,
            ConcernItem,
            ContentType,
        ) = models

        service_ct_id = ContentType.objects.get_for_model(ServiceModel).pk
        component_ct_id = ContentType.objects.get_for_model(ComponentModel).pk
        provider_ct_id = ContentType.objects.get_for_model(ProviderModel).pk

        prototypes = {}
        for type_ in ("cluster", "service", "component", "provider", "host"):
            prototypes[type_] = Prototype.objects.create(
                bundle=Bundle.objects.create(name=f"{type_}_bundle", version="1", hash="hash"),
                type=type_,
                name=f"{type_}_prototype",
                version="1",
            )

        provider = ProviderModel.objects.create(name="provider", prototype_id=prototypes["provider"].pk)
        host_0 = Host.objects.create(fqdn="host0", provider_id=provider.pk, prototype_id=prototypes["host"].pk)
        provider_chg = ConfigHostGroupModel.objects.create(
            object_type_id=provider_ct_id,
            object_id=provider.pk,
            name="provider_chg",
            config_id=ObjectConfig.objects.create(previous=1, current=2).pk,
        )
        provider_chg.hosts.add(host_0)

        cluster = Cluster.objects.create(name="cluster", prototype_id=prototypes["cluster"].pk)
        host_1 = Host.objects.create(
            fqdn="host1", provider_id=provider.pk, prototype_id=prototypes["host"].pk, cluster_id=cluster.pk
        )
        cluster_chg = ConfigHostGroupModel.objects.create(
            object_type_id=ContentType.objects.get_for_model(Cluster).pk,
            object_id=cluster.pk,
            name="cluster_chg",
            config_id=ObjectConfig.objects.create(previous=1, current=2).pk,
        )
        cluster_chg.hosts.add(host_1)

        service = ServiceModel.objects.create(cluster_id=cluster.pk, prototype_id=prototypes["service"].pk)
        host_2 = Host.objects.create(
            fqdn="host2", provider_id=provider.pk, prototype_id=prototypes["host"].pk, cluster_id=cluster.pk
        )
        service_chg = ConfigHostGroupModel.objects.create(
            object_type_id=service_ct_id,
            object_id=service.pk,
            name="service_chg",
            config_id=ObjectConfig.objects.create(previous=1, current=2).pk,
        )
        service_chg.hosts.add(host_2)

        component = ComponentModel.objects.create(
            cluster_id=cluster.pk, service_id=service.pk, prototype_id=prototypes["component"].pk
        )
        host_3 = Host.objects.create(
            fqdn="host3", provider_id=provider.pk, prototype_id=prototypes["host"].pk, cluster_id=cluster.pk
        )
        component_chg = ConfigHostGroupModel.objects.create(
            object_type_id=component_ct_id,
            object_id=component.pk,
            name="component_chg",
            config_id=ObjectConfig.objects.create(previous=1, current=2).pk,
        )
        component_chg.hosts.add(host_3)

        HostComponent.objects.create(
            cluster_id=cluster.pk, host_id=host_3.pk, service_id=service.pk, component_id=component.pk
        )
        ClusterBind.objects.create(
            cluster_id=cluster.pk, service_id=service.pk, source_cluster_id=cluster.pk, source_service_id=service.pk
        )

        for adcm_object, content_type_id in (
            (service, service_ct_id),
            (component, component_ct_id),
            (provider, provider_ct_id),
        ):
            common_kwargs = {"object_id": adcm_object.pk, "object_type_id": content_type_id}
            AnsibleConfig.objects.create(**common_kwargs, value={"va": "lue"})
            ActionHostGroup.objects.create(**common_kwargs, name="ahgname", description="ahgdescription")
            TaskLog.objects.create(**common_kwargs, status="created", owner_type="hostprovider")
            ConcernItem.objects.create(owner_id=adcm_object.pk, owner_type_id=content_type_id, cause="config")

    def _get_models(self, state: str) -> tuple:
        self.assertIn(state, {"old_state", "new_state"})

        if state == "old_state":
            service_model = "ClusterObject"
            component_model = "ServiceComponent"
            provider_model = "HostProvider"
            config_host_group_model = "GroupConfig"
        else:
            service_model = "Service"
            component_model = "Component"
            provider_model = "Provider"
            config_host_group_model = "ConfigHostGroup"

        state = getattr(self, state)

        Bundle = state.apps.get_model("cm", "Bundle")
        Prototype = state.apps.get_model("cm", "Prototype")

        Cluster = state.apps.get_model("cm", "Cluster")
        ServiceModel = state.apps.get_model("cm", service_model)
        ComponentModel = state.apps.get_model("cm", component_model)

        ClusterBind = state.apps.get_model("cm", "ClusterBind")
        HostComponent = state.apps.get_model("cm", "HostComponent")

        ProviderModel = state.apps.get_model("cm", provider_model)
        Host = state.apps.get_model("cm", "Host")

        ObjectConfig = state.apps.get_model("cm", "ObjectConfig")
        ConfigHostGroupModel = state.apps.get_model("cm", config_host_group_model)

        AnsibleConfig = state.apps.get_model("cm", "AnsibleConfig")
        ActionHostGroup = state.apps.get_model("cm", "ActionHostGroup")
        TaskLog = state.apps.get_model("cm", "TaskLog")
        ConcernItem = state.apps.get_model("cm", "ConcernItem")

        ContentType = state.apps.get_model("contenttypes", "ContentType")

        return (
            Bundle,
            Prototype,
            Cluster,
            ServiceModel,
            ComponentModel,
            ClusterBind,
            HostComponent,
            ProviderModel,
            Host,
            ObjectConfig,
            ConfigHostGroupModel,
            AnsibleConfig,
            ActionHostGroup,
            TaskLog,
            ConcernItem,
            ContentType,
        )

    def prepare(self):
        models = self._get_models(state="old_state")
        self._create_objects(*models)
        self.db_state = self._get_db_state(*models, state="old_state")

        Service, Component, Provider, ConfigHostGroup, TaskLog, ContentType = (
            models[3],
            models[4],
            models[7],
            models[10],
            models[-3],
            models[-1],
        )

        self.assertEqual(ContentType.objects.get_for_model(Service).model, "clusterobject")
        self.assertEqual(ContentType.objects.get_for_model(Component).model, "servicecomponent")
        self.assertEqual(ContentType.objects.get_for_model(Provider).model, "hostprovider")
        self.assertEqual(ContentType.objects.get_for_model(ConfigHostGroup).model, "groupconfig")

        self.assertSetEqual(set(TaskLog.objects.values_list("owner_type", flat=True)), {"hostprovider"})

    def test_migration_129_132(self):
        models = self._get_models(state="new_state")
        Service, Component, Provider, ConfigHostGroup, TaskLog, ContentType = (
            models[3],
            models[4],
            models[7],
            models[10],
            models[-3],
            models[-1],
        )

        self.assertDictEqual(self.db_state, self._get_db_state(*models, state="new_state"))

        self.assertEqual(ContentType.objects.get_for_model(Service).model, "service")
        self.assertEqual(ContentType.objects.get_for_model(Component).model, "component")
        self.assertEqual(ContentType.objects.get_for_model(Provider).model, "provider")
        self.assertEqual(ContentType.objects.get_for_model(ConfigHostGroup).model, "confighostgroup")

        self.assertSetEqual(set(TaskLog.objects.values_list("owner_type", flat=True)), {"provider"})
