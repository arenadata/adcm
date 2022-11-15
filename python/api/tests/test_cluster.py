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

from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.tests.base import BaseTestCase
from cm.models import Action, ActionType, Bundle, Cluster, Prototype, Upgrade


class TestClusterAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create(name="test_cluster_prototype")
        self.cluster_prototype = Prototype.objects.create(
            bundle=self.bundle,
            version=2,
            name="test_cluster_prototype",
        )
        self.cluster = Cluster.objects.create(prototype=self.cluster_prototype)

    def test_upgrade(self):
        Upgrade.objects.create(
            bundle=self.bundle,
            min_version=1,
            max_version=3,
            action=Action.objects.create(
                prototype=self.cluster_prototype,
                type=ActionType.Job,
                state_available="any",
            ),
        )
        response: Response = self.client.get(
            path=reverse("cluster-upgrade", kwargs={"cluster_id": self.cluster.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
