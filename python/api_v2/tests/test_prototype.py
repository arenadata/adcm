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
# pylint: disable=too-many-lines

from api_v2.tests.base import BaseAPITestCase
from cm.models import ObjectType, Prototype
from django.conf import settings
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK


class TestBundlePrototype(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_one"
        cluster_bundle_2_path = settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_one_upgrade"

        self.bundle_1 = self.add_bundle(source_dir=cluster_bundle_1_path)
        self.bundle_2 = self.add_bundle(source_dir=cluster_bundle_2_path)

        self.cluster_1_prototype: Prototype = self.bundle_1.prototype_set.filter(type=ObjectType.CLUSTER).first()

    def test_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:prototype-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 12)

    def test_versions_cluster_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:prototype-versions"), data={"type": ObjectType.CLUSTER.value}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(len(response.json()[0]["versions"]), 2)

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:prototype-detail", kwargs={"pk": self.cluster_1_prototype.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.cluster_1_prototype.pk)

    def test_accept_license_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:prototype-accept-license", kwargs={"pk": self.cluster_1_prototype.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.cluster_1_prototype.refresh_from_db(fields=["license"])
        self.assertEqual(self.cluster_1_prototype.license, "accepted")