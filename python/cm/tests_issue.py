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

import cm.api
import cm.issue
from cm.models import Bundle, Prototype, PrototypeImport, ClusterBind


class TestImport(TestCase):

    def cook_cluster(self, proto_name, cluster_name):
        b = Bundle.objects.create(name=proto_name, version='1.0')
        proto = Prototype.objects.create(type="cluster", name=proto_name, bundle=b)
        cluster = cm.api.add_cluster(proto, cluster_name)
        return (b, proto, cluster)

    def test_no_import(self):
        _, _, cluster = self.cook_cluster('Hadoop', 'Cluster1')
        self.assertEqual(cm.issue.do_check_import(cluster), (True, None))

    def test_import_requred(self):
        _, proto1, cluster = self.cook_cluster('Hadoop', 'Cluster1')
        PrototypeImport.objects.create(prototype=proto1, name='Monitoring', required=True)
        self.assertEqual(cm.issue.do_check_import(cluster), (False, None))

    def test_import_not_requred(self):
        _, proto1, cluster = self.cook_cluster('Hadoop', 'Cluster1')
        PrototypeImport.objects.create(prototype=proto1, name='Monitoring', required=False)
        self.assertEqual(cm.issue.do_check_import(cluster), (True, 'NOT_REQIURED'))

    def test_cluster_imported(self):
        _, proto1, cluster1 = self.cook_cluster('Hadoop', 'Cluster1')
        PrototypeImport.objects.create(prototype=proto1, name='Monitoring', required=True)

        _, _, cluster2 = self.cook_cluster('Monitoring', 'Cluster2')
        ClusterBind.objects.create(cluster=cluster1, source_cluster=cluster2)

        self.assertEqual(cm.issue.do_check_import(cluster1), (True, 'CLUSTER_IMPORTED'))

    def test_service_imported(self):
        _, proto1, cluster1 = self.cook_cluster('Hadoop', 'Cluster1')
        PrototypeImport.objects.create(prototype=proto1, name='Graphana', required=True)

        b2, _, cluster2 = self.cook_cluster('Monitoring', 'Cluster2')
        proto3 = Prototype.objects.create(type="service", name="Graphana", bundle=b2)
        service = cm.api.add_service_to_cluster(cluster2, proto3)
        ClusterBind.objects.create(
            cluster=cluster1, source_cluster=cluster2, source_service=service
        )

        self.assertEqual(cm.issue.do_check_import(cluster1), (True, 'SERVICE_IMPORTED'))

    def test_import_to_service(self):
        b1, _, cluster1 = self.cook_cluster('Hadoop', 'Cluster1')
        proto2 = Prototype.objects.create(type="service", name="YARN", bundle=b1)
        PrototypeImport.objects.create(prototype=proto2, name='Monitoring', required=True)
        service = cm.api.add_service_to_cluster(cluster1, proto2)

        _, _, cluster2 = self.cook_cluster('Monitoring', 'Cluster2')
        ClusterBind.objects.create(cluster=cluster1, service=service, source_cluster=cluster2)

        self.assertEqual(cm.issue.do_check_import(cluster1, service), (True, 'CLUSTER_IMPORTED'))

    def test_import_service_to_service(self):
        b1, _, cluster1 = self.cook_cluster('Hadoop', 'Cluster1')
        proto2 = Prototype.objects.create(type="service", name="YARN", bundle=b1)
        PrototypeImport.objects.create(prototype=proto2, name='Graphana', required=True)
        service1 = cm.api.add_service_to_cluster(cluster1, proto2)

        b2, _, cluster2 = self.cook_cluster('Monitoring', 'Cluster2')
        proto3 = Prototype.objects.create(type="service", name="Graphana", bundle=b2)
        service2 = cm.api.add_service_to_cluster(cluster2, proto3)
        ClusterBind.objects.create(
            cluster=cluster1, service=service1, source_cluster=cluster2, source_service=service2
        )

        self.assertEqual(cm.issue.do_check_import(cluster1, service1), (True, 'SERVICE_IMPORTED'))

    def test_issue_cluster_required_import(self):
        _, proto1, cluster1 = self.cook_cluster('Hadoop', 'Cluster1')
        PrototypeImport.objects.create(prototype=proto1, name='Monitoring', required=True)

        _, _, cluster2 = self.cook_cluster('Not_Monitoring', 'Cluster2')
        ClusterBind.objects.create(cluster=cluster1, source_cluster=cluster2)

        self.assertEqual(cm.issue.check_issue(cluster1), {'required_import': False})

    def test_issue_cluster_imported(self):
        _, proto1, cluster1 = self.cook_cluster('Hadoop', 'Cluster1')
        PrototypeImport.objects.create(prototype=proto1, name='Monitoring', required=True)

        _, _, cluster2 = self.cook_cluster('Monitoring', 'Cluster2')
        ClusterBind.objects.create(cluster=cluster1, source_cluster=cluster2)

        self.assertEqual(cm.issue.check_issue(cluster1), {})

    def test_issue_service_required_import(self):
        b1, _, cluster1 = self.cook_cluster('Hadoop', 'Cluster1')
        proto2 = Prototype.objects.create(type="service", name="YARN", bundle=b1)
        PrototypeImport.objects.create(prototype=proto2, name='Monitoring', required=True)
        service = cm.api.add_service_to_cluster(cluster1, proto2)

        _, _, cluster2 = self.cook_cluster('Non_Monitoring', 'Cluster2')
        ClusterBind.objects.create(cluster=cluster1, service=service, source_cluster=cluster2)

        self.assertEqual(cm.issue.check_issue(service), {'required_import': False})

    def test_issue_service_imported(self):
        b1, _, cluster1 = self.cook_cluster('Hadoop', 'Cluster1')
        proto2 = Prototype.objects.create(type="service", name="YARN", bundle=b1)
        PrototypeImport.objects.create(prototype=proto2, name='Monitoring', required=True)
        service = cm.api.add_service_to_cluster(cluster1, proto2)

        _, _, cluster2 = self.cook_cluster('Monitoring', 'Cluster2')
        ClusterBind.objects.create(cluster=cluster1, service=service, source_cluster=cluster2)

        self.assertEqual(cm.issue.check_issue(service), {})
