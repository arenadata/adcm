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
    migrate_from = ("cm", "0119_extract_sub_actions_from_actions")
    migrate_to = ("cm", "0120_adjust_paths")

    def prepare(self):
        Bundle = self.old_state.apps.get_model("cm", "Bundle")
        Prototype = self.old_state.apps.get_model("cm", "Prototype")
        PrototypeConfig = self.old_state.apps.get_model("cm", "PrototypeConfig")
        Action = self.old_state.apps.get_model("cm", "Action")
        SubAction = self.old_state.apps.get_model("cm", "SubAction")

        bundle = Bundle.objects.create(name="cool", version="342", hash="lfj21opfijoi")
        self.prototype_1 = Prototype.objects.create(
            bundle=bundle, type="cluster", name="protoname", version="200.400", path=".", license_path="fullpath"
        )
        self.prototype_2 = Prototype.objects.create(
            bundle=bundle, type="service", name="protonames", version="200.400", path="inner", license_path="./relpath"
        )
        self.prototype_3 = Prototype.objects.create(
            bundle=bundle, type="component", name="protonamec", version="200.400", path="more/inner/"
        )

        PrototypeConfig.objects.create(
            prototype=self.prototype_1, name="relative_root", type="text", default="./some.txt"
        )
        PrototypeConfig.objects.create(prototype=self.prototype_1, name="full_root", type="text", default="some.txt")
        PrototypeConfig.objects.create(
            prototype=self.prototype_1, name="control_root", type="string", default="./some.txt"
        )

        PrototypeConfig.objects.create(
            prototype=self.prototype_2, name="relative_inner", type="text", default="./some.txt"
        )
        PrototypeConfig.objects.create(
            prototype=self.prototype_2, name="full_inner", type="secrettext", default="some.txt"
        )
        PrototypeConfig.objects.create(
            prototype=self.prototype_2, name="control_inner", type="string", default="./some.txt"
        )

        PrototypeConfig.objects.create(
            prototype=self.prototype_3, name="relative_more_inner", type="secrettext", default="./some.txt"
        )
        PrototypeConfig.objects.create(
            prototype=self.prototype_3, name="full_more_inner", type="text", default="some.txt"
        )
        PrototypeConfig.objects.create(
            prototype=self.prototype_3, name="control_more_inner", type="string", default="./some.txt"
        )

        self.action_1 = Action.objects.create(
            prototype=self.prototype_1, config_jinja="./relative", name="relative_of_root", type="task"
        )
        self.action_2 = Action.objects.create(
            prototype=self.prototype_1, config_jinja="relative", name="full_of_root", type="task"
        )
        self.action_3 = Action.objects.create(
            prototype=self.prototype_2, config_jinja="./relative", name="relative_of_inner", type="task"
        )
        self.action_4 = Action.objects.create(
            prototype=self.prototype_2, config_jinja="something/relative", name="full_of_inner", type="task"
        )
        self.action_5 = Action.objects.create(
            prototype=self.prototype_3, config_jinja="./relative", name="relative_of_more_inner", type="task"
        )
        self.action_6 = Action.objects.create(
            prototype=self.prototype_3, config_jinja="relative", name="full_of_more_inner", type="task"
        )
        self.action_7 = Action.objects.create(prototype=self.prototype_3, config_jinja=None, name="empty", type="task")

        self.sub_1 = SubAction.objects.create(
            action=self.action_1, name="relative", script="./here.yaml", script_type="ansible"
        )
        self.sub_2 = SubAction.objects.create(
            action=self.action_3, name="full", script="here.yaml", script_type="ansible"
        )
        self.sub_3 = SubAction.objects.create(
            action=self.action_5, name="relative_inner", script="./over/there.yaml", script_type="ansible"
        )

    def test_migration_0118_0119_move_data(self):
        Action = self.new_state.apps.get_model("cm", "Action")
        SubAction = self.new_state.apps.get_model("cm", "SubAction")
        Prototype = self.new_state.apps.get_model("cm", "Prototype")
        PrototypeConfig = self.new_state.apps.get_model("cm", "PrototypeConfig")

        expected = {
            "relative_of_root": "relative",
            "full_of_root": "relative",
            "relative_of_inner": "inner/relative",
            "full_of_inner": "something/relative",
            "relative_of_more_inner": "more/inner/relative",
            "full_of_more_inner": "relative",
            "empty": None,
        }
        actual = dict(Action.objects.values_list("name", "config_jinja"))
        self.assertEqual(actual, expected)

        expected = {"relative": "here.yaml", "full": "here.yaml", "relative_inner": "more/inner/over/there.yaml"}
        actual = dict(SubAction.objects.values_list("name", "script"))
        self.assertEqual(actual, expected)

        expected = {"protoname": "fullpath", "protonames": "inner/relpath", "protonamec": None}
        actual = dict(Prototype.objects.values_list("name", "license_path"))
        self.assertEqual(actual, expected)

        expected = {
            "relative_root": "some.txt",
            "full_root": "some.txt",
            "control_root": "./some.txt",
            "relative_inner": "inner/some.txt",
            "full_inner": "some.txt",
            "control_inner": "./some.txt",
            "relative_more_inner": "more/inner/some.txt",
            "full_more_inner": "some.txt",
            "control_more_inner": "./some.txt",
        }
        actual = dict(PrototypeConfig.objects.values_list("name", "default"))
        self.assertEqual(actual, expected)
