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

from cm.models import ConcernType


class TestDirectMigration(MigratorTestCase):
    migrate_from = ("cm", "0121_delete_MessageTemplate")
    migrate_to = ("cm", "0123_flag_autogeneration_object")

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

    def test_migration_0121_and_0123_move_data(self):
        Prototype = self.new_state.apps.get_model("cm", "Prototype")
        ConcernItem = self.new_state.apps.get_model("cm", "ConcernItem")

        self.assertEqual(Prototype.objects.count(), 5)
        self.assertEqual(Prototype.objects.filter(flag_autogeneration={"adcm_outdated_config": False}).count(), 5)

        self.assertEqual(ConcernItem.objects.count(), len(self.will_stay))
        self.assertSetEqual(
            set(ConcernItem.objects.values_list("id", flat=True)), {concern.id for concern in self.will_stay}
        )
