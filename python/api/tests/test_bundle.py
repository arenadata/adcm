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

from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_409_CONFLICT

from adcm.tests.base import BaseTestCase
from cm.models import Bundle, Prototype


class TestBundle(BaseTestCase):
    # pylint: disable=too-many-public-methods

    def setUp(self) -> None:
        super().setUp()

        self.bundle_1 = Bundle.objects.create(
            name="test_bundle_1",
            version="123",
            version_order=1,
        )
        self.bundle_2 = Bundle.objects.create(name="test_bundle_2", version="456", version_order=2)
        Prototype.objects.create(
            bundle=self.bundle_1, name=self.bundle_1.name, license_path="some_path", license="unaccepted"
        )
        Prototype.objects.create(bundle=self.bundle_2, name=self.bundle_2.name)

    def test_upload_bundle(self) -> None:
        self.upload_bundle(path=self.test_bundle_path)

        self.assertTrue(Path(settings.DOWNLOAD_DIR, self.test_bundle_filename).exists())

    def test_load_bundle(self):
        self.upload_bundle(path=self.test_bundle_path)
        self.load_bundle(path=self.test_bundle_path)

    def test_load_bundle_wrong_cluster_mm_action_no_host_action_prop_fail(self):
        bundle_filename = "bundle_test_cluster_wrong_host_action.tar"

        self.upload_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files",
                bundle_filename,
            )
        )

        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": bundle_filename},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "INVALID_OBJECT_DEFINITION")

    def test_load_bundle_wrong_cluster_mm_action_false_host_action_prop_fail(self):
        bundle_filename = "bundle_test_cluster_false_host_action.tar"

        self.upload_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files",
                bundle_filename,
            )
        )

        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": bundle_filename},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "INVALID_OBJECT_DEFINITION")

    def test_load_bundle_cluster_mm_action_host_action_true_success(self):
        bundle_filename = "bundle_test_cluster_host_action_true.tar"

        self.upload_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files",
                bundle_filename,
            )
        )

        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": bundle_filename},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_load_bundle_service_with_host_mm_action_fail(self):
        bundle_filename = "bundle_test_service_with_host_action.tar"

        self.upload_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files",
                bundle_filename,
            )
        )

        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": bundle_filename},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "INVALID_OBJECT_DEFINITION")

    def test_load_bundle_cluster_with_host_mm_has_ui_options_fail(self):
        bundle_filename = "bundle_test_cluster_action_with_ui_options.tar"

        self.upload_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files",
                bundle_filename,
            )
        )

        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": bundle_filename},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "INVALID_OBJECT_DEFINITION")

    def test_load_servicemap(self):
        with patch("api.stack.views.load_service_map"):
            response: Response = self.client.put(
                path=reverse("load-servicemap"),
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_list(self):
        response: Response = self.client.get(path=reverse("bundle-list"))

        self.assertEqual(len(response.data["results"]), 2)

    def test_list_filter_name(self):
        response: Response = self.client.get(reverse("bundle-list"), {"name": self.bundle_1.name})

        self.assertEqual(response.data["results"][0]["id"], self.bundle_1.pk)

    def test_list_filter_version(self):
        response: Response = self.client.get(reverse("bundle-list"), {"version": self.bundle_1.version})

        self.assertEqual(response.data["results"][0]["id"], self.bundle_1.pk)

    def test_list_ordering_name(self):
        response: Response = self.client.get(reverse("bundle-list"), {"ordering": "name"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.bundle_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.bundle_2.pk)

    def test_list_ordering_name_reverse(self):
        response: Response = self.client.get(reverse("bundle-list"), {"ordering": "-name"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.bundle_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.bundle_1.pk)

    def test_list_ordering_version_order(self):
        response: Response = self.client.get(reverse("bundle-list"), {"ordering": "version_order"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.bundle_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.bundle_2.pk)

    def test_list_ordering_version_order_reverse(self):
        response: Response = self.client.get(reverse("bundle-list"), {"ordering": "-version_order"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.bundle_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.bundle_1.pk)

    def test_retrieve(self):
        response: Response = self.client.get(
            path=reverse("bundle-detail", kwargs={"bundle_pk": self.bundle_2.pk}),
        )

        self.assertEqual(response.data["id"], self.bundle_2.pk)

    def test_delete(self):
        with patch("cm.bundle.shutil.rmtree"):
            self.client.delete(
                path=reverse("bundle-detail", kwargs={"bundle_pk": self.bundle_2.pk}),
            )

        self.assertFalse(Bundle.objects.filter(pk=self.bundle_2.pk))

    def test_update(self):
        with patch("api.stack.views.update_bundle"):
            response: Response = self.client.put(
                path=reverse("bundle-update", kwargs={"bundle_pk": self.bundle_1.pk}),
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_license(self):
        with patch("api.stack.views.get_license", return_value="license body"):
            response: Response = self.client.get(
                path=reverse("bundle-license", kwargs={"bundle_pk": self.bundle_1.pk}),
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_accept_license(self):
        response: Response = self.client.put(
            path=reverse("accept-license", kwargs={"bundle_pk": self.bundle_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_distinct(self):
        self.upload_and_load_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files/bundle_cluster_requires.tar",
            )
        )
        self.upload_and_load_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files/test_bundle_distinct_1.tar",
            )
        )
        self.upload_and_load_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files/test_bundle_distinct_2.tar",
            )
        )

        response: Response = self.client.get(
            reverse("cluster-prototype-list"),
            {
                "fields": "display_name",
                "distinct": 1,
                "ordering": "display_name",
                "limit": 50,
                "offset": 0,
                "view": "interface",
            },
        )

        self.assertEqual(response.data["count"], 2)
