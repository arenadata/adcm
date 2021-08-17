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

from django.test import TestCase

from cm import models
from cm.unit_tests import utils


class ADCMEntityConcernTest(TestCase):
    """Tests for `cm.models.ADCMEntity` lock-related methods"""

    def setUp(self):
        self.hierarchy = utils.generate_hierarchy()

    def test_is_locked__false(self):
        for obj in self.hierarchy.values():
            self.assertFalse(obj.is_locked)

            for item in obj.concerns.all():
                self.assertFalse(item, 'No locks expected')

    def test_is_locked__true(self):
        lock = utils.gen_concern_item(models.ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)
            self.assertTrue(obj.is_locked)

    def test_is_locked__deleted(self):
        lock = utils.gen_concern_item(models.ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)

        lock.delete()
        for obj in self.hierarchy.values():
            self.assertFalse(obj.is_locked)

    def test_add_to_concern__none(self):
        lock = None
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)
            self.assertFalse(obj.is_locked)

    def test_add_to_concern__deleted(self):
        lock = models.ConcernItem(type=models.ConcernType.Lock, name=None, reason='unsaved')
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)
            self.assertFalse(obj.is_locked)

    def test_add_to_concern(self):
        lock = utils.gen_concern_item(models.ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)
            self.assertTrue(obj.is_locked)
            locks = obj.concerns.all()
            self.assertEqual(len(locks), 1)
            self.assertEqual(locks[0].pk, lock.pk)

    def test_remove_from_concern__none(self):
        nolock = None
        lock = utils.gen_concern_item(models.ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)
            obj.remove_from_concerns(nolock)
            self.assertTrue(obj.is_locked)

    def test_remove_from_concern__deleted(self):
        nolock = models.ConcernItem(type=models.ConcernType.Lock, name=None, reason='unsaved')
        lock = utils.gen_concern_item(models.ConcernType.Lock)
        for obj in self.hierarchy.values():
            obj.add_to_concerns(lock)
            obj.remove_from_concerns(nolock)
            self.assertTrue(obj.is_locked)

    def test_get_own_issue__empty(self):
        cluster = self.hierarchy['cluster']
        self.assertIsNone(cluster.get_own_issue(models.IssueType.Config))

    def test_get_own_issue__others(self):
        cluster = self.hierarchy['cluster']
        service = self.hierarchy['service']
        reason = models.MessageTemplate.get_message_from_template(
            models.MessageTemplate.KnownNames.ConfigIssue.value, source=cluster
        )
        issue_type = models.IssueType.Config
        issue_name = issue_type.gen_issue_name(cluster)
        issue = models.ConcernItem.objects.create(
            type=models.ConcernType.Issue, name=issue_name, reason=reason
        )
        cluster.add_to_concerns(issue)
        service.add_to_concerns(issue)
        self.assertIsNone(service.get_own_issue(issue_type))

    def test_get_own_issue__exists(self):
        cluster = self.hierarchy['cluster']
        reason = models.MessageTemplate.get_message_from_template(
            models.MessageTemplate.KnownNames.ConfigIssue.value, source=cluster
        )
        issue_type = models.IssueType.Config
        issue_name = issue_type.gen_issue_name(cluster)
        issue = models.ConcernItem.objects.create(
            type=models.ConcernType.Issue, name=issue_name, reason=reason
        )
        cluster.add_to_concerns(issue)
        self.assertIsNotNone(cluster.get_own_issue(issue_type))
