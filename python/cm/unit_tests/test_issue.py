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

from cm import issue, models
from cm.unit_tests import utils
from cm.hierarchy import Tree


class CreateIssueTest(TestCase):
    """Tests for `cm.issue.create_issues()`"""

    def setUp(self) -> None:
        self.hierarchy = utils.generate_hierarchy()
        self.cluster = self.hierarchy['cluster']
        self.tree = Tree(self.cluster)

    def test_new_issue(self):
        issue_type = models.IssueType.Config
        issue.create_issue(self.cluster, issue_type)
        own_issue = self.cluster.get_own_issue(issue_type)
        self.assertIsNotNone(own_issue)
        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = list(node.value.concerns.all())
            self.assertEqual(len(concerns), 1)
            self.assertEqual(own_issue.pk, concerns[0].pk)

    def test_same_issue(self):
        issue_type = models.IssueType.Config
        issue.create_issue(self.cluster, issue_type)
        issue.create_issue(self.cluster, issue_type)  # create twice
        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = list(node.value.concerns.all())
            self.assertEqual(len(concerns), 1)  # exist only one

    def test_few_issues(self):
        issue_type_1 = models.IssueType.Config
        issue_type_2 = models.IssueType.RequiredImport
        issue.create_issue(self.cluster, issue_type_1)
        issue.create_issue(self.cluster, issue_type_2)
        own_issue_1 = self.cluster.get_own_issue(issue_type_1)
        self.assertIsNotNone(own_issue_1)
        own_issue_2 = self.cluster.get_own_issue(issue_type_2)
        self.assertIsNotNone(own_issue_2)
        self.assertNotEqual(own_issue_1.pk, own_issue_2.pk)
        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = {c.pk for c in node.value.concerns.all()}
            self.assertEqual(len(concerns), 2)
            self.assertSetEqual({own_issue_1.pk, own_issue_2.pk}, concerns)


class RemoveIssueTest(TestCase):
    """Tests for `cm.issue.create_issues()`"""

    def setUp(self) -> None:
        self.hierarchy = utils.generate_hierarchy()
        self.cluster = self.hierarchy['cluster']
        self.tree = Tree(self.cluster)

    def test_no_issue(self):
        issue_type = models.IssueType.Config
        self.assertIsNone(self.cluster.get_own_issue(issue_type))
        issue.remove_issue(self.cluster, issue_type)
        self.assertIsNone(self.cluster.get_own_issue(issue_type))

    def test_single_issue(self):
        issue_type = models.IssueType.Config
        issue.create_issue(self.cluster, issue_type)

        issue.remove_issue(self.cluster, issue_type)
        self.assertIsNone(self.cluster.get_own_issue(issue_type))
        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = list(node.value.concerns.all())
            self.assertEqual(len(concerns), 0)

    def test_few_issues(self):
        issue_type_1 = models.IssueType.Config
        issue_type_2 = models.IssueType.RequiredImport
        issue.create_issue(self.cluster, issue_type_1)
        issue.create_issue(self.cluster, issue_type_2)

        issue.remove_issue(self.cluster, issue_type_1)
        own_issue_1 = self.cluster.get_own_issue(issue_type_1)
        self.assertIsNone(own_issue_1)
        own_issue_2 = self.cluster.get_own_issue(issue_type_2)
        self.assertIsNotNone(own_issue_2)

        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = [c.pk for c in node.value.concerns.all()]
            self.assertEqual(len(concerns), 1)
            self.assertEqual(concerns[0], own_issue_2.pk)
