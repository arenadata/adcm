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


class TestDirectMigration(MigratorTestCase):
    migrate_from = ("cm", "0134_bundle_bundle_lower_name_idx_and_more")
    migrate_to = ("cm", "0135_remove_stale_ansibleconfig_actionhostgroup_entries")

    def prepare(self) -> None:
        ContentType = self.old_state.apps.get_model("contenttypes", "ContentType")
        AnsibleConfig = self.old_state.apps.get_model("cm", "AnsibleConfig")
        ActionHostGroup = self.old_state.apps.get_model("cm", "ActionHostGroup")
        Bundle = self.old_state.apps.get_model("cm", "Bundle")
        Prototype = self.old_state.apps.get_model("cm", "Prototype")

        Cluster = self.old_state.apps.get_model("cm", "Cluster")
        cluster_ct = ContentType.objects.get_for_model(Cluster)

        Service = self.old_state.apps.get_model("cm", "Service")
        service_ct = ContentType.objects.get_for_model(Service)

        Component = self.old_state.apps.get_model("cm", "Component")
        component_ct = ContentType.objects.get_for_model(Component)

        prototypes = {}
        for type_ in ("cluster", "service", "component"):
            prototypes[type_] = Prototype.objects.create(
                bundle=Bundle.objects.create(name=f"{type_}_bundle", version="1", hash="hash"),
                type=type_,
                name=f"{type_}_prototype",
                version="1",
            )

        cluster = Cluster.objects.create(prototype_id=prototypes["cluster"].id, name="cluster")
        service = Service.objects.create(prototype_id=prototypes["service"].id, cluster_id=cluster.id)
        component = Component.objects.create(
            prototype_id=prototypes["component"].id, cluster_id=cluster.id, service_id=service.id
        )

        # ensure these ids are not taken
        self.assertSetEqual({200, 201, 202, 203} - {cluster.id, service.id, component.id}, {200, 201, 202, 203})

        stale_ansible_config = AnsibleConfig.objects.create(object_id=200, object_type_id=cluster_ct.id)
        stale_cluster_ahg = ActionHostGroup.objects.create(
            object_id=201, object_type_id=cluster_ct.id, name="stale cluster ahg", description="."
        )
        stale_service_ahg = ActionHostGroup.objects.create(
            object_id=202, object_type_id=service_ct.id, name="stale service ahg", description="."
        )
        stale_component_ahg = ActionHostGroup.objects.create(
            object_id=203, object_type_id=component_ct.id, name="stale component ahg", description="."
        )

        cluster_ansible_config = AnsibleConfig.objects.create(object_id=cluster.id, object_type_id=cluster_ct.id)
        cluster_ahg = ActionHostGroup.objects.create(
            object_id=cluster.id, object_type_id=cluster_ct.id, name="cluster ahg", description="."
        )
        service_ahg = ActionHostGroup.objects.create(
            object_id=service.id, object_type_id=service_ct.id, name="service ahg", description="."
        )
        component_ahg = ActionHostGroup.objects.create(
            object_id=component.id, object_type_id=component_ct.id, name="component ahg", description="."
        )

        self.expected = {
            "ansiblecfg": {
                "stay": {cluster_ansible_config.id},
                "gone": {stale_ansible_config.id},
            },
            "ahg": {
                "stay": {cluster_ahg.id, service_ahg.id, component_ahg.id},
                "gone": {stale_cluster_ahg.id, stale_service_ahg.id, stale_component_ahg.id},
            },
        }

    def test_migration_0134_0135(self):
        AnsibleConfig = self.new_state.apps.get_model("cm", "AnsibleConfig")
        ActionHostGroup = self.new_state.apps.get_model("cm", "ActionHostGroup")

        self.assertFalse(AnsibleConfig.objects.filter(id__in=self.expected["ansiblecfg"]["gone"]).exists())
        self.assertSetEqual(
            set(AnsibleConfig.objects.values_list("id", flat=True)),
            self.expected["ansiblecfg"]["stay"],
        )

        self.assertFalse(ActionHostGroup.objects.filter(id__in=self.expected["ahg"]["gone"]).exists())
        self.assertSetEqual(
            set(ActionHostGroup.objects.values_list("id", flat=True)),
            self.expected["ahg"]["stay"],
        )
