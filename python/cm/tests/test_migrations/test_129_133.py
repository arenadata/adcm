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
    migrate_from = ("cm", "0129_auto_20240904_1045")
    migrate_to = ("cm", "0133_restore_fk_fields_after_rename_clusterobject_to_service")

    @staticmethod
    def _get_db_state(*models) -> dict:
        (
            *_,
            Cluster,
            ServiceModel,
            ServiceComponent,
            ClusterBind,
            HostComponent,
            HostProvider,
            Host,
            ContentType,
            AnsibleConfig,
            ActionHostGroup,
            GroupConfig,
            TaskLog,
            ConcernItem,
        ) = models

        return {
            "cluster": tuple(Cluster.objects.values_list("id", "prototype_id")),
            "service": tuple(ServiceModel.objects.values_list("id", "cluster_id", "prototype_id")),
            "component": tuple(ServiceComponent.objects.values_list("id", "cluster_id", "service_id", "prototype_id")),
            "provider": tuple(HostProvider.objects.values_list("id", "prototype_id")),
            "host": tuple(Host.objects.values_list("id", "cluster_id", "prototype_id")),
            "host_component": tuple(
                HostComponent.objects.values_list("id", "cluster_id", "host_id", "service_id", "component_id")
            ),
            "cluster_bind": tuple(
                ClusterBind.objects.values_list(
                    "id", "cluster_id", "service_id", "source_cluster_id", "source_service_id"
                )
            ),
            "service_ct_id": ContentType.objects.get_for_model(ServiceModel).pk,
            "ansible_config": tuple(AnsibleConfig.objects.values_list("id", "object_id", "object_type_id")),
            "action_host_group": tuple(ActionHostGroup.objects.values_list("id", "object_id", "object_type_id")),
            "group_config": tuple(GroupConfig.objects.values_list("id", "object_id", "object_type_id")),
            "task_log": tuple(TaskLog.objects.values_list("id", "object_id", "object_type_id")),
            "concern_item": tuple(ConcernItem.objects.values_list("id", "owner_id", "owner_type_id")),
        }

    @staticmethod
    def _create_objects(*models):
        (
            Bundle,
            Prototype,
            Cluster,
            ServiceModel,
            ServiceComponent,
            ClusterBind,
            HostComponent,
            HostProvider,
            Host,
            ContentType,
            AnsibleConfig,
            ActionHostGroup,
            GroupConfig,
            TaskLog,
            ConcernItem,
        ) = models

        prototypes = {}
        for type_ in ("cluster", "service", "component", "provider", "host"):
            prototypes[type_] = Prototype.objects.create(
                bundle=Bundle.objects.create(name=f"{type_}_bundle", version="1", hash="hash"),
                type=type_,
                name=f"{type_}_prototype",
                version="1",
            )

        cluster = Cluster.objects.create(name="cluster", prototype_id=prototypes["cluster"].pk)
        service = ServiceModel.objects.create(cluster_id=cluster.pk, prototype_id=prototypes["service"].pk)
        component = ServiceComponent.objects.create(
            cluster_id=cluster.pk, service_id=service.pk, prototype_id=prototypes["component"].pk
        )
        provider = HostProvider.objects.create(name="provider", prototype_id=prototypes["provider"].pk)
        host = Host.objects.create(
            fqdn="host", provider_id=provider.pk, prototype_id=prototypes["host"].pk, cluster_id=cluster.pk
        )

        HostComponent.objects.create(
            cluster_id=cluster.pk, host_id=host.pk, service_id=service.pk, component_id=component.pk
        )
        ClusterBind.objects.create(
            cluster_id=cluster.pk, service_id=service.pk, source_cluster_id=cluster.pk, source_service_id=service.pk
        )

        service_ct_id = ContentType.objects.get_for_model(ServiceModel).pk
        common_kwargs = {"object_id": service.pk, "object_type_id": service_ct_id}
        AnsibleConfig.objects.create(**common_kwargs, value={"va": "lue"})
        ActionHostGroup.objects.create(**common_kwargs, name="ahgname", description="ahgdescription")
        GroupConfig.objects.create(**common_kwargs, name="gcname")
        TaskLog.objects.create(**common_kwargs, status="created")
        ConcernItem.objects.create(owner_id=service.pk, owner_type_id=service_ct_id, cause="config")

    def _get_models(self, state: str) -> tuple:
        self.assertIn(state, {"old_state", "new_state"})

        service_model = "ClusterObject" if state == "old_state" else "Service"
        state = getattr(self, state)

        Bundle = state.apps.get_model("cm", "Bundle")
        Prototype = state.apps.get_model("cm", "Prototype")

        Cluster = state.apps.get_model("cm", "Cluster")
        ServiceModel = state.apps.get_model("cm", service_model)
        ServiceComponent = state.apps.get_model("cm", "ServiceComponent")

        ClusterBind = state.apps.get_model("cm", "ClusterBind")
        HostComponent = state.apps.get_model("cm", "HostComponent")

        HostProvider = state.apps.get_model("cm", "HostProvider")
        Host = state.apps.get_model("cm", "Host")

        ContentType = state.apps.get_model("contenttypes", "ContentType")

        AnsibleConfig = state.apps.get_model("cm", "AnsibleConfig")
        ActionHostGroup = state.apps.get_model("cm", "ActionHostGroup")
        GroupConfig = state.apps.get_model("cm", "GroupConfig")
        TaskLog = state.apps.get_model("cm", "TaskLog")
        ConcernItem = state.apps.get_model("cm", "ConcernItem")

        return (
            Bundle,
            Prototype,
            Cluster,
            ServiceModel,
            ServiceComponent,
            ClusterBind,
            HostComponent,
            HostProvider,
            Host,
            ContentType,
            AnsibleConfig,
            ActionHostGroup,
            GroupConfig,
            TaskLog,
            ConcernItem,
        )

    def prepare(self):
        models = self._get_models(state="old_state")
        self._create_objects(*models)
        self.db_state = self._get_db_state(*models)

        ContentType, ServiceModel = models[-6], models[3]
        self.assertEqual(ContentType.objects.get_for_model(ServiceModel).model, "clusterobject")

    def test_migration_129_133(self):
        models = self._get_models(state="new_state")
        ContentType, ServiceModel = models[-6], models[3]

        self.assertDictEqual(self.db_state, self._get_db_state(*models))
        self.assertEqual(ContentType.objects.get_for_model(ServiceModel).model, "service")
