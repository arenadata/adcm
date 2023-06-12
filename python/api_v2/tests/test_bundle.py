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

from api_v2.tests.base import BaseAPITestCase
from django.conf import settings
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)


class TestBundle(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_one"

        self.bundle_1 = self.add_bundle(source_dir=cluster_bundle_1_path)

        cluster_new_bundle_path = settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_two"
        self.new_bundle_file = self.prepare_bundle_file(source_dir=cluster_new_bundle_path)

    def test_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:bundle-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_upload_success(self):
        with open(settings.DOWNLOAD_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = self.client.post(
                path=reverse(viewname="v2:bundle-list"),
                data={"file": f},
                format="multipart",
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_retrieve_success(self):
        response = self.client.get(path=reverse(viewname="v2:bundle-detail", kwargs={"pk": self.bundle_1.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.bundle_1.pk)

    def test_retrieve_not_found_fail(self):
        response = self.client.get(path=reverse(viewname="v2:bundle-detail", kwargs={"pk": self.bundle_1.pk + 1}))

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_delete_success(self):
        response = self.client.delete(path=reverse(viewname="v2:bundle-detail", kwargs={"pk": self.bundle_1.pk}))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_delete_not_found_fail(self):
        response = self.client.delete(path=reverse(viewname="v2:bundle-detail", kwargs={"pk": self.bundle_1.pk + 1}))

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
