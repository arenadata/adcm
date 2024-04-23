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


class TestDirectMigration(MigratorTestCase):
    migrate_from = ("cm", "0118_post_autonomous_joblogs")
    migrate_to = ("cm", "0119_extract_sub_actions_from_actions")

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

    def test_migration_0118_0119_move_data(self):
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
    migrate_from = ("cm", "0119_extract_sub_actions_from_actions")
    migrate_to = ("cm", "0118_post_autonomous_joblogs")

    def prepare(self):
        Prototype = self.old_state.apps.get_model("cm", "Prototype")
        Bundle = self.old_state.apps.get_model("cm", "Bundle")
        bundle = Bundle.objects.create(name="cool", version="342", hash="lfj21opfijoi")
        prototype = Prototype.objects.create(bundle=bundle, type="cluster", name="protoname", version="200.400")

        Action = self.old_state.apps.get_model("cm", "Action")
        SubAction = self.old_state.apps.get_model("cm", "SubAction")

        self.action_1_data = {
            "script": "path/to/script.yaml",
            "script_type": ScriptType.ANSIBLE.value,
            "state_on_fail": "failme",
            "multi_state_on_fail_set": ["nice"],
            "multi_state_on_fail_unset": ["cool"],
            "params": {"ansible_tags": "some,thing,better", "jinja2_native": "yes", "custom": {"arbitrary": "stuff"}},
        }
        self.action_1 = Action.objects.create(
            prototype=prototype,
            name="simple_job",
            type="job",
            state_on_success="best",
            multi_state_on_success_set=["coolest"],
            multi_state_on_success_unset=[],
            allow_to_terminate=True,
            state_on_fail="another",
            multi_state_on_fail_set=["custom"],
            multi_state_on_fail_unset=self.action_1_data["multi_state_on_fail_unset"],
        )
        self.action_1_sub = SubAction.objects.create(
            action_id=self.action_1.pk, name="another_name", display_name="another time", **self.action_1_data
        )

        self.action_2 = Action.objects.create(
            prototype=prototype,
            name="simple_task",
            type="task",
            state_on_success="best",
            multi_state_on_success_set=["coolest"],
            multi_state_on_success_unset=[],
            **{k: v for k, v in self.action_1_data.items() if k not in {"script", "script_type", "params"}},
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
        )
        self.action_3_sub = SubAction.objects.create(
            action_id=self.action_3.pk, name=self.action_3.name, **self.action_3_data
        )

        self.sub_action_pre_migration_amount = SubAction.objects.count()

    def test_migration_0119_to_0118_move_data(self):
        Action = self.new_state.apps.get_model("cm", "Action")
        SubAction = self.new_state.apps.get_model("cm", "SubAction")

        self.assertEqual(Action.objects.count(), 3)
        # 1 for each "job" typed action
        self.assertEqual(SubAction.objects.count(), self.sub_action_pre_migration_amount - 2)

        new_action_1 = Action.objects.get(id=self.action_1.pk)

        self.assertEqual(new_action_1.name, self.action_1.name)
        self.assertEqual(new_action_1.display_name, self.action_1.display_name)
        self.assertEqual(new_action_1.script, self.action_1_data["script"])
        self.assertEqual(new_action_1.script_type, self.action_1_data["script_type"])
        self.assertEqual(new_action_1.params, self.action_1_data["params"])
        self.assertEqual(new_action_1.state_on_fail, self.action_1.state_on_fail)
        self.assertEqual(new_action_1.multi_state_on_fail_set, self.action_1.multi_state_on_fail_set)
        self.assertEqual(new_action_1.multi_state_on_fail_unset, self.action_1_data["multi_state_on_fail_unset"])
        self.assertTrue(new_action_1.allow_to_terminate)

        new_action_3 = Action.objects.get(id=self.action_3.pk)

        self.assertEqual(new_action_3.name, self.action_3.name)
        self.assertEqual(new_action_3.display_name, self.action_3.display_name)
        self.assertEqual(new_action_3.script, self.action_3_data["script"])
        self.assertEqual(new_action_3.script_type, self.action_3_data["script_type"])
        self.assertEqual(new_action_3.params, self.action_3_data["params"])
        self.assertEqual(new_action_3.state_on_fail, self.action_3.state_on_fail)
        self.assertEqual(new_action_3.multi_state_on_fail_set, self.action_3.multi_state_on_fail_set)
        self.assertEqual(new_action_3.multi_state_on_fail_unset, self.action_3.multi_state_on_fail_unset)
        self.assertFalse(new_action_3.allow_to_terminate)
