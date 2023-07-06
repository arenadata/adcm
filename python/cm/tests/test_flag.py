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

from cm.flag import create_flag, get_flag_name, remove_flag, update_flags
from cm.hierarchy import Tree
from cm.models import ConcernCause, ConcernItem, ConcernType
from cm.tests.utils import generate_hierarchy

from adcm.tests.base import BaseTestCase


class FlagTest(BaseTestCase):
    """Tests for `cm.issue.create_issues()`"""

    def setUp(self) -> None:
        super().setUp()

        self.hierarchy = generate_hierarchy()
        self.cluster = self.hierarchy["cluster"]
        self.cluster.prototype.allow_flags = True
        self.cluster.prototype.save(update_fields=["allow_flags"])
        self.tree = Tree(self.cluster)

    def test_create_flag(self):
        create_flag(obj=self.cluster)
        flag = ConcernItem.objects.filter(type=ConcernType.FLAG, name=get_flag_name(obj=self.cluster)).first()

        self.assertIsNotNone(flag)
        self.assertEqual(flag.owner, self.cluster)
        reason = {
            "message": "${source} has an outdated configuration",
            "placeholder": {
                "source": {"type": "cluster", "name": self.cluster.name, "ids": {"cluster": self.cluster.id}}
            },
        }
        self.assertEqual(flag.reason, reason)
        self.assertEqual(flag.cause, ConcernCause.CONFIG)

    def test_update_flags(self):
        update_flags(obj=self.cluster)
        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = node.value.concerns.all()
            self.assertEqual(concerns.count(), 1)
            self.assertEqual(ConcernType.FLAG.value, concerns.first().type)

    def test_unique_flag_name(self):
        msg = "Test message"
        update_flags(obj=self.cluster)
        update_flags(obj=self.cluster, msg=msg)
        concerns = self.cluster.concerns.all()
        self.assertEqual(concerns.count(), 2)

        # test what flag with the same name will not create and not apply second time
        update_flags(obj=self.cluster)
        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = node.value.concerns.all()
            self.assertEqual(concerns.count(), 2)
            self.assertEqual(ConcernType.FLAG.value, concerns.first().type)

    def test_delete_flag_success(self):
        msg = "Test message"
        update_flags(obj=self.cluster)
        update_flags(obj=self.cluster, msg=msg)

        remove_flag(obj=self.cluster)
        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = node.value.concerns.all()
            self.assertEqual(concerns.count(), 1)
            self.assertEqual(ConcernType.FLAG.value, concerns.first().type)
            self.assertEqual(concerns.first().name, get_flag_name(obj=self.cluster, msg=msg))
