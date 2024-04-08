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
from core.job.types import ScriptType
from django_test_migrations.contrib.unittest_case import MigratorTestCase

from cm.models import ConcernType


class TestDirectMigration(MigratorTestCase):
    migrate_from = ("cm", "0117_post_autonomous_joblogs")
    migrate_to = ("cm", "0118_extract_sub_actions_from_actions")

    def prepare(self):
        Prototype = self.old_state.apps.get_model("cm", "Prototype")
        Bundle = self.old_state.apps.get_model("cm", "Bundle")
        bundle = Bundle.objects.create(name="cool", version="342", hash="lfj21opfijoi")
        prototype = Prototype.objects.create(bundle=bundle, type="cluster", name="protoname", version="200.400")

        Action = self.old_state.apps.get_model("cm", "Action")
        SubAction = self.old_state.apps.get_model("cm", "SubAction")

        self.action_1_data = {
            "name": "simple_job",
            "display_name": "Awesome And Simple",
            "script": "path/to/script.yaml",
            "script_type": ScriptType.ANSIBLE.value,
            "state_on_fail": "failme",
            "multi_state_on_fail_set": [],
            "multi_state_on_fail_unset": ["cool"],
            "params": {"ansible_tags": "some,thing,better", "jinja2_native": "yes", "custom": {"arbitrary": "stuff"}},
        }
        self.action_1 = Action.objects.create(
            prototype=prototype,
            type="job",
            state_on_success="best",
            multi_state_on_success_set=["coolest"],
            multi_state_on_success_unset=[],
            allow_to_terminate=True,
            **self.action_1_data,
        )

        self.action_2 = Action.objects.create(
            prototype=prototype,
            type="task",
            state_on_success="best",
            multi_state_on_success_set=["coolest"],
            multi_state_on_success_unset=[],
            **self.action_1_data | {"name": "simple_task"},
        )
        self.action_2_sub_1 = SubAction.objects.create(
            action_id=self.action_2.pk,
            name="step_1",
            script="boom.lala",
            script_type=ScriptType.ANSIBLE.value,
            multi_state_on_fail_set=["heh"],
            params={"another": "stuff"},
        )
        self.action_2_sub_2 = SubAction.objects.create(
            action_id=self.action_2.pk,
            name="step_2",
            script="bundle_switch",
            script_type=ScriptType.INTERNAL.value,
            multi_state_on_fail_unset=["hoho"],
        )

        self.action_3_data = {"script": "./relative.py", "script_type": ScriptType.PYTHON.value, "params": {}}
        self.action_3 = Action.objects.create(
            prototype=prototype,
            name="another_job",
            type="job",
            state_on_success="nothing",
            multi_state_on_success_set=[],
            multi_state_on_success_unset=["abs"],
            allow_to_terminate=False,
            **self.action_3_data,
        )

        self.sub_action_pre_migration_amount = SubAction.objects.count()

    def test_migration_0117_0118_move_data(self):
        Action = self.new_state.apps.get_model("cm", "Action")
        SubAction = self.new_state.apps.get_model("cm", "SubAction")

        self.assertEqual(Action.objects.count(), 3)
        # 1 for each "job" typed action
        self.assertEqual(SubAction.objects.count(), self.sub_action_pre_migration_amount + 2)

        new_action_1_sub = SubAction.objects.get(action_id=self.action_1.pk)

        for key, value in self.action_1_data.items():
            self.assertEqual(getattr(new_action_1_sub, key), value)
        self.assertTrue(new_action_1_sub.allow_to_terminate)

        new_action_3_sub = SubAction.objects.get(action_id=self.action_3.pk)

        self.assertEqual(new_action_3_sub.name, self.action_3.name)
        self.assertEqual(new_action_3_sub.display_name, self.action_3.display_name)
        self.assertEqual(new_action_3_sub.script, self.action_3_data["script"])
        self.assertEqual(new_action_3_sub.script_type, self.action_3_data["script_type"])
        self.assertEqual(new_action_3_sub.params, {})
        self.assertEqual(new_action_3_sub.state_on_fail, "")
        self.assertEqual(new_action_3_sub.multi_state_on_fail_set, [])
        self.assertEqual(new_action_3_sub.multi_state_on_fail_unset, [])
        self.assertFalse(new_action_3_sub.allow_to_terminate)


class TestReverseMigration(MigratorTestCase):
    migrate_from = ("cm", "0119_delete_MessageTemplate")
    migrate_to = ("cm", "0121_flag_autogeneration_object")

    def prepare(self):
        Prototype = self.old_state.apps.get_model("cm", "Prototype")
        Bundle = self.old_state.apps.get_model("cm", "Bundle")
        for i in range(5):
            Prototype.objects.create(
                bundle=Bundle.objects.create(name=f"cool-{i}", version="342", hash="lfj21opfijoi"),
                type="cluster",
                name=f"protoname-{i}",
                version="200.400",
            )

        ConcernItem = self.old_state.apps.get_model("cm", "ConcernItem")
        ContentType = self.old_state.apps.get_model("contenttypes", "ContentType")
        content_type = ContentType.objects.create(app_label="cm", model="cluster")

        self.will_stay = [
            ConcernItem.objects.create(
                type=ConcernType.ISSUE,
                name="issue_with_owner",
                owner_id=4,
                owner_type=content_type,
            ),
            ConcernItem.objects.create(
                type=ConcernType.FLAG,
                name="FLAG_with_owner",
                owner_id=2,
                owner_type=content_type,
            ),
            ConcernItem.objects.create(
                type=ConcernType.LOCK,
                name="lock_with_owner",
                owner_id=1,
                owner_type=content_type,
            ),
        ]
        self.will_be_gone = [
            ConcernItem.objects.create(
                type=ConcernType.ISSUE,
                name="issue_wo_owner",
                owner_id=4,
                owner_type=None,
            ),
            ConcernItem.objects.create(
                type=ConcernType.FLAG,
                name="FLAG_wo_owner",
                owner_id=None,
                owner_type=None,
            ),
            ConcernItem.objects.create(
                type=ConcernType.LOCK,
                name="lock_wo_owner",
                owner_id=None,
                owner_type=content_type,
            ),
        ]

    def test_migration_0120_and_0121_move_data(self):
        Prototype = self.new_state.apps.get_model("cm", "Prototype")
        ConcernItem = self.new_state.apps.get_model("cm", "ConcernItem")

        self.assertEqual(Prototype.objects.count(), 5)
        self.assertEqual(Prototype.objects.filter(flag_autogeneration={"adcm_outdated_config": False}).count(), 5)

        self.assertEqual(ConcernItem.objects.count(), len(self.will_stay))
        self.assertSetEqual(
            set(ConcernItem.objects.values_list("id", flat=True)), {concern.id for concern in self.will_stay}
        )
