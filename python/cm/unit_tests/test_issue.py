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

from unittest.mock import patch
from django.test import TestCase

from cm.unit_tests import utils
from cm import issue
from cm.hierarchy import Tree


def generate_hierarchy():  # pylint: disable=too-many-locals,too-many-statements
    """
    Generates hierarchy:
        cluster - service - component - host - provider
    """
    utils.gen_adcm()
    cluster_bundle = utils.gen_bundle()
    provider_bundle = utils.gen_bundle()
    cluster_pt = utils.gen_prototype(cluster_bundle, 'cluster')
    cluster = utils.gen_cluster(prototype=cluster_pt)
    service_pt = utils.gen_prototype(cluster_bundle, 'service')
    service = utils.gen_service(cluster, prototype=service_pt)
    component_pt = utils.gen_prototype(cluster_bundle, 'component')
    component = utils.gen_component(service, prototype=component_pt)
    provider_pt = utils.gen_prototype(provider_bundle, 'provider')
    provider = utils.gen_provider(prototype=provider_pt)
    host_pt = utils.gen_prototype(provider_bundle, 'host')
    host = utils.gen_host(provider, prototype=host_pt)
    utils.gen_host_component(component, host)
    return dict(
        cluster=cluster,
        service=service,
        component=component,
        provider=provider,
        host=host,
    )


class AggregateIssuesTest(TestCase):
    """
    Tests for `cm.issue.aggregate_issues()`
    BEWARE of different object instances in `self.tree` and `self.hierarchy`, use `refresh_from_db`
    """
    def setUp(self) -> None:
        self.hierarchy = generate_hierarchy()
        self.tree = Tree(self.hierarchy['cluster'])

    def test_no_issues(self):
        """Objects with no issues has no aggregated issues as well"""
        for obj in self.hierarchy.values():
            self.assertFalse(issue.aggregate_issues(obj, self.tree))

    def test_provider_issue(self):
        """Test provider's special case - it does not aggregate issues from other objects"""
        data = {'config': False}
        for node in self.tree.get_all_affected(self.tree.built_from):
            node.value.issue = data
            node.value.save()

        provider = self.hierarchy['provider']
        provider.refresh_from_db()
        self.assertDictEqual(data, issue.aggregate_issues(provider, self.tree))

    def test_own_issue(self):
        """Test if own issue is not doubled as nested"""
        data = {'config': False}
        for node in self.tree.get_all_affected(self.tree.built_from):
            node.value.issue = data
            node.value.save()

        for name, obj in self.hierarchy.items():
            obj.refresh_from_db()
            agg_issue = issue.aggregate_issues(obj, self.tree)
            self.assertNotIn(name, agg_issue)
            self.assertIn('config', agg_issue)

    def test_linked_issues(self):
        """Test if aggregated issue has issues from all linked objects"""
        data = {'config': False}
        for node in self.tree.get_all_affected(self.tree.built_from):
            node.value.issue = data
            node.value.save()

        keys = {'config', 'cluster', 'service', 'component', 'provider', 'host'}
        for name, obj in self.hierarchy.items():
            if name == 'provider':
                continue

            obj.refresh_from_db()
            agg_issue = issue.aggregate_issues(obj, self.tree)
            expected_keys = keys.difference({name})
            got_keys = set(agg_issue.keys())
            self.assertSetEqual(expected_keys, got_keys)


class IssueReporterTest(TestCase):
    @patch('cm.status_api.post_event')
    def test_update__no_issue_changes(self, mock_evt_post):
        hierarchy = generate_hierarchy()
        issue.update_hierarchy_issues(hierarchy['cluster'])
        mock_evt_post.assert_not_called()

    @patch('cm.status_api.post_event')
    @patch('cm.issue.check_cluster_issue')
    def test_update__raise_issue(self, mock_check, mock_evt_post):
        mock_check.return_value = {'config': False}
        hierarchy = generate_hierarchy()

        issue.update_hierarchy_issues(hierarchy['cluster'])

        affected = ('cluster', 'service', 'component', 'host')
        self.assertEqual(len(affected), mock_evt_post.call_count)
        expected_calls = {('raise_issue', n) for n in affected}
        got_calls = set()
        for call in mock_evt_post.mock_calls:
            got_calls.add((call.args[0], call.args[1]))
        self.assertSetEqual(expected_calls, got_calls)

    @patch('cm.status_api.post_event')
    @patch('cm.issue.check_cluster_issue')
    def test_update__clear_issue(self, mock_check, mock_evt_post):
        mock_check.return_value = {}
        hierarchy = generate_hierarchy()
        hierarchy['cluster'].issue = {'config': False}
        hierarchy['cluster'].save()

        issue.update_hierarchy_issues(hierarchy['cluster'])

        affected = ('cluster', 'service', 'component', 'host')
        self.assertEqual(len(affected), mock_evt_post.call_count)
        expected_calls = {('clear_issue', n) for n in affected}
        got_calls = set()
        for call in mock_evt_post.mock_calls:
            got_calls.add((call.args[0], call.args[1]))
        self.assertSetEqual(expected_calls, got_calls)
