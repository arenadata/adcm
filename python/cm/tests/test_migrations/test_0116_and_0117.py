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
    migrate_from = ("cm", "0115_auto_20231025_1823")
    migrate_to = ("cm", "0117_post_autonomous_joblogs")

    def prepare(self):
        TaskLog = self.old_state.apps.get_model("cm", "TaskLog")
        JobLog = self.old_state.apps.get_model("cm", "JobLog")
        Action = self.old_state.apps.get_model("cm", "Action")
        SubAction = self.old_state.apps.get_model("cm", "SubAction")
        Prototype = self.old_state.apps.get_model("cm", "Prototype")
        Bundle = self.old_state.apps.get_model("cm", "Bundle")
        Cluster = self.old_state.apps.get_model("cm", "Cluster")

        ContentType = self.old_state.apps.get_model("contenttypes", "ContentType")

        bundle = Bundle.objects.create(name="cool", version="342", hash="lfj21opfijoi")
        prototype = Prototype.objects.create(bundle=bundle, type="cluster", name="protoname", version="200.400")

        cluster = Cluster.objects.create(prototype=prototype, name="bazar")

        action = Action.objects.create(
            prototype=prototype,
            name="reg_name",
            display_name="Name To Display",
            type="task",
            script="sc",
            script_type=ScriptType.ANSIBLE,
            allow_to_terminate=True,
        )

        self.sub_1 = SubAction.objects.create(
            action=action,
            name="sub_1",
            display_name="Number One",
            allow_to_terminate=False,
            script="script1",
            script_type=ScriptType.ANSIBLE,
            state_on_fail="onfail",
            multi_state_on_fail_set=["one", "two"],
            multi_state_on_fail_unset=["old"],
        )
        self.sub_2 = SubAction.objects.create(
            action=action,
            name="sub_2",
            display_name="Second",
            allow_to_terminate=None,
            script="script2",
            script_type=ScriptType.PYTHON,
            state_on_fail="onfailtwo",
            multi_state_on_fail_set=[],
            multi_state_on_fail_unset=["hello"],
        )
        self.sub_3 = SubAction.objects.create(
            action=action, name="sub_3", allow_to_terminate=True, script="script1", script_type=ScriptType.INTERNAL
        )

        task = TaskLog.objects.create(
            action=action, object_id=cluster.pk, object_type=ContentType.objects.create(app_label="cm", model="cluster")
        )
        self.job_1 = JobLog.objects.create(action=action, task=task, sub_action=self.sub_1)
        self.job_2 = JobLog.objects.create(action=action, task=task, sub_action=self.sub_2)
        self.job_3 = JobLog.objects.create(action=action, task=task, sub_action=self.sub_3)
        self.job_4 = JobLog.objects.create(action=action, task=task, sub_action=None)

    def test_migration_0116_0117_move_data(self):
        Action = self.new_state.apps.get_model("cm", "Action")
        JobLog = self.new_state.apps.get_model("cm", "JobLog")

        self.assertEqual(Action.objects.count(), 1)

        for job_, sub_ in ((self.job_1, self.sub_1), (self.job_2, self.sub_2), (self.job_3, self.sub_3)):
            job = JobLog.objects.get(pk=job_.pk)
            for field in (
                "name",
                "display_name",
                "script",
                "script_type",
                "state_on_fail",
                "multi_state_on_fail_set",
                "multi_state_on_fail_unset",
            ):
                self.assertEqual(getattr(job, field), getattr(sub_, field))

        self.assertSetEqual(
            set(JobLog.objects.values_list("id", "allow_to_terminate").all()),
            {(self.job_1.pk, False), (self.job_2.pk, True), (self.job_3.pk, True), (self.job_4.pk, False)},
        )
