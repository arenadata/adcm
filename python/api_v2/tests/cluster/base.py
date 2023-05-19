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

from cm.models import Bundle, Cluster, ObjectType, Prototype

from adcm.tests.base import BaseTestCase


class ClusterBaseTestCase(BaseTestCase):
    # pylint: disable=too-many-instance-attributes

    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.cluster_1_prototype_name = "test_cluster_1_prototype"
        self.cluster_1_prototype = Prototype.objects.create(
            bundle=self.bundle,
            name=self.cluster_1_prototype_name,
            type=ObjectType.CLUSTER,
            version="1",
        )

        self.cluster_2_prototype_name = "test_cluster_2_prototype"
        self.cluster_2_prototype = Prototype.objects.create(
            bundle=self.bundle,
            name=self.cluster_2_prototype_name,
            type=ObjectType.CLUSTER,
            version="1",
        )
        Prototype.objects.create(
            bundle=self.bundle,
            name=self.cluster_2_prototype_name,
            type=ObjectType.CLUSTER,
            version="2",
        )

        self.cluster_1_name = "test_cluster_1"
        self.cluster_1 = Cluster.objects.create(prototype=self.cluster_1_prototype, name=self.cluster_1_name)

        self.cluster_2_name = "test_cluster_2"
        self.cluster_2 = Cluster.objects.create(prototype=self.cluster_2_prototype, name=self.cluster_2_name)
