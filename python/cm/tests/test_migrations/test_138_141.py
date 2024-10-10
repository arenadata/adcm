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
    migrate_from = ("cm", "0138_rename_table_groupconfig_to_confighostgroup")
    migrate_to = ("cm", "0141_return_FKs_to_Provider")

    @staticmethod
    def _get_db_state(*models) -> dict:
        (
            *_,
            ProviderModel,
            Host,
            AnsibleConfig,
            ActionHostGroup,
            ConfigHostGroup,
            TaskLog,
            ConcernItem,
            ContentType,
        ) = models

        return {
            "provider": tuple(ProviderModel.objects.values_list("id", "prototype_id")),
            "host": tuple(Host.objects.values_list("id", "cluster_id", "prototype_id", "provider_id")),
            "provider_ct_id": ContentType.objects.get_for_model(ProviderModel).pk,
            "ansible_config": tuple(AnsibleConfig.objects.values_list("id", "object_id", "object_type_id")),
            "action_host_group": tuple(ActionHostGroup.objects.values_list("id", "object_id", "object_type_id")),
            "config_host_group": tuple(ConfigHostGroup.objects.values_list("id", "object_id", "object_type_id")),
            "task_log": tuple(TaskLog.objects.values_list("id", "object_id", "object_type_id")),
            "concern_item": tuple(ConcernItem.objects.values_list("id", "owner_id", "owner_type_id")),
        }

    @staticmethod
    def _create_objects(*models):
        (
            Bundle,
            Prototype,
            ProviderModel,
            Host,
            AnsibleConfig,
            ActionHostGroup,
            ConfigHostGroup,
            TaskLog,
            ConcernItem,
            ContentType,
        ) = models

        prototypes = {}
        for type_ in ("provider", "host"):
            prototypes[type_] = Prototype.objects.create(
                bundle=Bundle.objects.create(name=f"{type_}_bundle", version="1", hash="hash"),
                type=type_,
                name=f"{type_}_prototype",
                version="1",
            )

        provider = ProviderModel.objects.create(name="provider", prototype_id=prototypes["provider"].pk)
        Host.objects.create(fqdn="host", provider_id=provider.pk, prototype_id=prototypes["host"].pk)

        provider_ct_id = ContentType.objects.get_for_model(ProviderModel).pk
        common_kwargs = {"object_id": provider.pk, "object_type_id": provider_ct_id}
        AnsibleConfig.objects.create(**common_kwargs, value={"va": "lue"})
        ActionHostGroup.objects.create(**common_kwargs, name="ahgname", description="ahgdescription")
        ConfigHostGroup.objects.create(**common_kwargs, name="chgname")
        TaskLog.objects.create(**common_kwargs, status="created")
        ConcernItem.objects.create(owner_id=provider.pk, owner_type_id=provider_ct_id, cause="config")

    def _get_models(self, state: str) -> tuple:
        self.assertIn(state, {"old_state", "new_state"})

        provider_model = "HostProvider" if state == "old_state" else "Provider"
        state = getattr(self, state)

        Bundle = state.apps.get_model("cm", "Bundle")
        Prototype = state.apps.get_model("cm", "Prototype")

        ProviderModel = state.apps.get_model("cm", provider_model)
        Host = state.apps.get_model("cm", "Host")

        AnsibleConfig = state.apps.get_model("cm", "AnsibleConfig")
        ActionHostGroup = state.apps.get_model("cm", "ActionHostGroup")
        ConfigHostGroup = state.apps.get_model("cm", "ConfigHostGroup")
        TaskLog = state.apps.get_model("cm", "TaskLog")
        ConcernItem = state.apps.get_model("cm", "ConcernItem")

        ContentType = state.apps.get_model("contenttypes", "ContentType")

        return (
            Bundle,
            Prototype,
            ProviderModel,
            Host,
            AnsibleConfig,
            ActionHostGroup,
            ConfigHostGroup,
            TaskLog,
            ConcernItem,
            ContentType,
        )

    def prepare(self):
        models = self._get_models(state="old_state")
        self._create_objects(*models)
        self.db_state = self._get_db_state(*models)

        ProviderModel, ContentType = models[2], models[-1]
        self.assertEqual(ContentType.objects.get_for_model(ProviderModel).model, "hostprovider")

    def test_migration_138_141(self):
        models = self._get_models(state="new_state")
        ProviderModel, ContentType = models[2], models[-1]

        self.assertDictEqual(self.db_state, self._get_db_state(*models))
        self.assertEqual(ContentType.objects.get_for_model(ProviderModel).model, "provider")
