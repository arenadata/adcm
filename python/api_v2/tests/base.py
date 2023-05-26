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
from cm.models import Action, Cluster, ConfigLog, Prototype
from django.conf import settings
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_201_CREATED

from adcm.tests.base import BaseTestCase


class BaseTestCaseAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle_file_1 = settings.BASE_DIR / "python" / "api_v2" / "tests" / "files" / "cluster_one.tar"
        bundle_file_2 = settings.BASE_DIR / "python" / "api_v2" / "tests" / "files" / "cluster_two.tar"
        self.bundle_1 = self.upload_and_load_bundle(path=bundle_file_1)
        self.bundle_2 = self.upload_and_load_bundle(path=bundle_file_2)
        self.cluster_1 = self.create_cluster(bundle_pk=self.bundle_1.pk, name="cluster")
        self.cluster_1_config = ConfigLog.objects.get(id=self.cluster_1.config.current)
        self.cluster_1_action = Action.objects.filter(prototype=self.cluster_1.prototype).first()
        self.cluster_2 = self.create_cluster(bundle_pk=self.bundle_2.pk, name="cluster_2")

    def create_cluster(self, bundle_pk: int, name: str) -> Cluster:
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={
                "prototype": Prototype.objects.filter(bundle_id=bundle_pk, type="cluster").first().pk,
                "name": name,
                "description": name,
            },
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        return Cluster.objects.get(pk=response.json()["id"])
