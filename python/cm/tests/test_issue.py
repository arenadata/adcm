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
from operator import attrgetter
from typing import Iterable
from unittest.mock import patch

from adcm.tests.base import BaseTestCase

from cm.api import add_cluster, add_service_to_cluster
from cm.hierarchy import Tree
from cm.issue import (
    add_concern_to_object,
    create_issue,
    do_check_import,
    recheck_issues,
    remove_issue,
    update_hierarchy_issues,
)
from cm.models import (
    ADCMEntity,
    Bundle,
    ClusterBind,
    ConcernCause,
    ConcernItem,
    ConcernType,
    Prototype,
    PrototypeImport,
)
from cm.services.cluster import perform_host_to_cluster_map
from cm.services.status import notify
from cm.tests.utils import gen_service, generate_hierarchy

mock_issue_check_map = {
    ConcernCause.CONFIG: lambda x: False,
    ConcernCause.IMPORT: lambda x: True,
    ConcernCause.SERVICE: lambda x: False,
    ConcernCause.HOSTCOMPONENT: lambda x: True,
    ConcernCause.REQUIREMENT: lambda x: True,
}


class CreateIssueTest(BaseTestCase):
    """Tests for `cm.issue.create_issues()`"""

    def setUp(self) -> None:
        super().setUp()

        self.hierarchy = generate_hierarchy()
        self.cluster = self.hierarchy["cluster"]
        self.tree = Tree(self.cluster)

    def test_new_issue(self):
        """Test if new issue is propagated to all affected objects"""

        issue_type = ConcernCause.CONFIG
        create_issue(self.cluster, issue_type)
        own_issue = self.cluster.get_own_issue(issue_type)

        self.assertIsNotNone(own_issue)

        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = list(node.value.concerns.all())

            self.assertEqual(len(concerns), 1)
            self.assertEqual(own_issue.pk, concerns[0].pk)

    def test_same_issue(self):
        """Test if issue could not be added more than once"""

        issue_type = ConcernCause.CONFIG
        create_issue(self.cluster, issue_type)
        create_issue(self.cluster, issue_type)  # create twice
        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = list(node.value.concerns.all())

            self.assertEqual(len(concerns), 1)  # exist only one

    def test_few_issues(self):
        """Test if object could have more than one issue"""

        issue_type_1 = ConcernCause.CONFIG
        issue_type_2 = ConcernCause.IMPORT
        create_issue(self.cluster, issue_type_1)
        create_issue(self.cluster, issue_type_2)
        own_issue_1 = self.cluster.get_own_issue(issue_type_1)

        self.assertIsNotNone(own_issue_1)

        own_issue_2 = self.cluster.get_own_issue(issue_type_2)

        self.assertIsNotNone(own_issue_2)
        self.assertNotEqual(own_issue_1.pk, own_issue_2.pk)

        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = {c.pk for c in node.value.concerns.all()}

            self.assertEqual(len(concerns), 2)
            self.assertSetEqual({own_issue_1.pk, own_issue_2.pk}, concerns)

    @patch("cm.issue._issue_check_map", mock_issue_check_map)
    def test_inherit_on_creation(self):
        """Test if new object in hierarchy inherits existing issues"""

        issue_type = ConcernCause.CONFIG
        create_issue(self.cluster, issue_type)
        cluster_issue = self.cluster.get_own_issue(issue_type)
        new_service = gen_service(self.cluster, self.cluster.prototype.bundle)

        self.assertListEqual(list(new_service.concerns.all()), [])

        update_hierarchy_issues(new_service)
        new_service_issues = [i.id for i in new_service.concerns.all()]

        self.assertIn(cluster_issue.id, new_service_issues)

    def test_required_service_issue(self):
        service_prototype = Prototype.objects.create(
            type="service", bundle=self.cluster.prototype.bundle, required=True, name="required service"
        )
        update_hierarchy_issues(obj=self.cluster)
        cluster_issue = self.cluster.concerns.filter(cause=ConcernCause.SERVICE).first()
        self.assertEqual(cluster_issue.cause, ConcernCause.SERVICE)
        self.assertEqual(cluster_issue.reason["placeholder"]["target"]["name"], service_prototype.name)


class RemoveIssueTest(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.hierarchy = generate_hierarchy()
        self.cluster = self.hierarchy["cluster"]
        self.tree = Tree(self.cluster)

    def test_no_issue(self):
        issue_type = ConcernCause.CONFIG

        self.assertIsNone(self.cluster.get_own_issue(issue_type))

        remove_issue(self.cluster, issue_type)

        self.assertIsNone(self.cluster.get_own_issue(issue_type))

    def test_single_issue(self):
        issue_type = ConcernCause.CONFIG
        create_issue(self.cluster, issue_type)

        remove_issue(self.cluster, issue_type)

        self.assertIsNone(self.cluster.get_own_issue(issue_type))

        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = list(node.value.concerns.all())

            self.assertEqual(len(concerns), 0)

    def test_few_issues(self):
        issue_type_1 = ConcernCause.CONFIG
        issue_type_2 = ConcernCause.IMPORT
        create_issue(self.cluster, issue_type_1)
        create_issue(self.cluster, issue_type_2)

        remove_issue(self.cluster, issue_type_1)
        own_issue_1 = self.cluster.get_own_issue(issue_type_1)

        self.assertIsNone(own_issue_1)

        own_issue_2 = self.cluster.get_own_issue(issue_type_2)

        self.assertIsNotNone(own_issue_2)

        for node in self.tree.get_directly_affected(self.tree.built_from):
            concerns = [c.pk for c in node.value.concerns.all()]

            self.assertEqual(len(concerns), 1)
            self.assertEqual(concerns[0], own_issue_2.pk)


class TestImport(BaseTestCase):
    @staticmethod
    def cook_cluster(proto_name, cluster_name):
        bundle = Bundle.objects.create(name=proto_name, version="1.0")
        proto = Prototype.objects.create(type="cluster", name=proto_name, bundle=bundle)
        cluster = add_cluster(proto, cluster_name)

        return bundle, proto, cluster

    def test_no_import(self):
        _, _, cluster = self.cook_cluster("Hadoop", "Cluster1")

        self.assertEqual(do_check_import(cluster), (True, None))

    def test_import_required(self):
        _, proto1, cluster = self.cook_cluster("Hadoop", "Cluster1")
        PrototypeImport.objects.create(prototype=proto1, name="Monitoring", required=True)

        self.assertEqual(do_check_import(cluster), (False, None))

    def test_import_not_required(self):
        _, proto1, cluster = self.cook_cluster("Hadoop", "Cluster1")
        PrototypeImport.objects.create(prototype=proto1, name="Monitoring", required=False)

        self.assertEqual(do_check_import(cluster), (True, "NOT_REQUIRED"))

    def test_cluster_imported(self):
        _, proto1, cluster1 = self.cook_cluster("Hadoop", "Cluster1")
        PrototypeImport.objects.create(prototype=proto1, name="Monitoring", required=True)

        _, _, cluster2 = self.cook_cluster("Monitoring", "Cluster2")
        ClusterBind.objects.create(cluster=cluster1, source_cluster=cluster2)

        self.assertEqual(do_check_import(cluster1), (True, "CLUSTER_IMPORTED"))

    def test_service_imported(self):
        _, proto1, cluster1 = self.cook_cluster("Hadoop", "Cluster1")
        PrototypeImport.objects.create(prototype=proto1, name="Graphana", required=True)

        bundle_2, _, cluster2 = self.cook_cluster("Monitoring", "Cluster2")
        proto3 = Prototype.objects.create(type="service", name="Graphana", bundle=bundle_2)
        service = add_service_to_cluster(cluster2, proto3)
        ClusterBind.objects.create(cluster=cluster1, source_cluster=cluster2, source_service=service)

        self.assertEqual(do_check_import(cluster1), (True, "SERVICE_IMPORTED"))

    def test_import_to_service(self):
        bundle_1, _, cluster1 = self.cook_cluster("Hadoop", "Cluster1")
        proto2 = Prototype.objects.create(type="service", name="YARN", bundle=bundle_1)
        PrototypeImport.objects.create(prototype=proto2, name="Monitoring", required=True)
        service = add_service_to_cluster(cluster1, proto2)

        _, _, cluster2 = self.cook_cluster("Monitoring", "Cluster2")
        ClusterBind.objects.create(cluster=cluster1, service=service, source_cluster=cluster2)

        self.assertEqual(do_check_import(cluster1, service), (True, "CLUSTER_IMPORTED"))

    def test_import_service_to_service(self):
        bundle_1, _, cluster1 = self.cook_cluster("Hadoop", "Cluster1")
        proto2 = Prototype.objects.create(type="service", name="YARN", bundle=bundle_1)
        PrototypeImport.objects.create(prototype=proto2, name="Graphana", required=True)
        service1 = add_service_to_cluster(cluster1, proto2)

        bundle_2, _, cluster2 = self.cook_cluster("Monitoring", "Cluster2")
        proto3 = Prototype.objects.create(type="service", name="Graphana", bundle=bundle_2)
        service2 = add_service_to_cluster(cluster2, proto3)
        ClusterBind.objects.create(
            cluster=cluster1,
            service=service1,
            source_cluster=cluster2,
            source_service=service2,
        )

        self.assertEqual(do_check_import(cluster1, service1), (True, "SERVICE_IMPORTED"))

    def test_issue_cluster_required_import(self):
        _, proto1, cluster1 = self.cook_cluster("Hadoop", "Cluster1")
        PrototypeImport.objects.create(prototype=proto1, name="Monitoring", required=True)

        _, _, cluster2 = self.cook_cluster("Not_Monitoring", "Cluster2")
        ClusterBind.objects.create(cluster=cluster1, source_cluster=cluster2)

        recheck_issues(cluster1)
        issue = cluster1.get_own_issue(ConcernCause.IMPORT)

        self.assertIsNotNone(issue)

    def test_issue_cluster_imported(self):
        _, proto1, cluster1 = self.cook_cluster("Hadoop", "Cluster1")
        PrototypeImport.objects.create(prototype=proto1, name="Monitoring", required=True)

        _, _, cluster2 = self.cook_cluster("Monitoring", "Cluster2")
        ClusterBind.objects.create(cluster=cluster1, source_cluster=cluster2)

        recheck_issues(cluster1)
        issue = cluster1.get_own_issue(ConcernCause.IMPORT)

        self.assertIsNone(issue)

    def test_issue_service_required_import(self):
        bundle_1, _, cluster1 = self.cook_cluster("Hadoop", "Cluster1")
        proto2 = Prototype.objects.create(type="service", name="YARN", bundle=bundle_1)
        PrototypeImport.objects.create(prototype=proto2, name="Monitoring", required=True)
        service = add_service_to_cluster(cluster1, proto2)

        _, _, cluster2 = self.cook_cluster("Non_Monitoring", "Cluster2")
        ClusterBind.objects.create(cluster=cluster1, service=service, source_cluster=cluster2)

        recheck_issues(service)
        issue = service.get_own_issue(ConcernCause.IMPORT)

        self.assertIsNotNone(issue)

    def test_issue_service_imported(self):
        bundle_1, _, cluster1 = self.cook_cluster("Hadoop", "Cluster1")
        proto2 = Prototype.objects.create(type="service", name="YARN", bundle=bundle_1)
        PrototypeImport.objects.create(prototype=proto2, name="Monitoring", required=True)
        service = add_service_to_cluster(cluster1, proto2)

        _, _, cluster2 = self.cook_cluster("Monitoring", "Cluster2")
        ClusterBind.objects.create(cluster=cluster1, service=service, source_cluster=cluster2)

        recheck_issues(service)
        issue = service.get_own_issue(ConcernCause.IMPORT)

        self.assertIsNone(issue)


class TestConcernsRedistribution(BaseTestCase):
    MOCK_ISSUE_CHECK_MAP_ALL_FALSE = {
        ConcernCause.CONFIG: lambda x: False,
        ConcernCause.IMPORT: lambda x: False,
        ConcernCause.SERVICE: lambda x: False,
        ConcernCause.HOSTCOMPONENT: lambda x: False,
        ConcernCause.REQUIREMENT: lambda x: False,
    }

    def setUp(self) -> None:
        super().setUp()

        self.hierarchy = generate_hierarchy(bind_to_cluster=False)
        self.cluster = self.hierarchy["cluster"]
        self.service = self.hierarchy["service"]
        self.component = self.hierarchy["component"]
        self.hostprovider = self.hierarchy["provider"]
        self.host = self.hierarchy["host"]

        for object_ in self.hierarchy.values():
            create_issue(object_, ConcernCause.CONFIG)
            tree = Tree(object_)
            self.add_lock(
                owner=object_, affected_objects=map(attrgetter("value"), tree.get_all_affected(node=tree.built_from))
            )

    def add_lock(self, owner: ADCMEntity, affected_objects: Iterable[ADCMEntity]):
        """Check out lock_affected_objects"""
        lock = ConcernItem.objects.create(
            type=ConcernType.LOCK.value,
            name=None,
            reason=f"Lock from {owner.__class__.__name__} {owner.id}",
            blocking=True,
            owner=owner,
            cause=ConcernCause.JOB.value,
        )
        for obj in affected_objects:
            add_concern_to_object(object_=obj, concern=lock)

    def test_map_host_to_cluster(self) -> None:
        concerns_before = self.host.concerns.all()
        self.assertEqual(len(concerns_before), 4)
        self.assertEqual(
            set(map(attrgetter("owner_type"), concerns_before)),
            {self.hostprovider.content_type, self.host.content_type},
        )

        with patch("cm.issue._issue_check_map", self.MOCK_ISSUE_CHECK_MAP_ALL_FALSE):
            perform_host_to_cluster_map(self.cluster.id, [self.host.id], status_service=notify)

        self.host.refresh_from_db()
        concerns_after = self.host.concerns.all()
        self.assertEqual(len(concerns_after), 4)
        self.assertEqual(
            set(map(attrgetter("owner_type"), concerns_after)), {self.hostprovider.content_type, self.host.content_type}
        )
