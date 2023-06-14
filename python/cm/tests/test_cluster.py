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

import string

from cm.models import Bundle, Cluster, Prototype
from django.urls import reverse
from rest_framework import status

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestCluster(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.allowed_name_chars_start_end = f"{string.ascii_letters}{string.digits}"
        self.allowed_name_chars_middle = f"{self.allowed_name_chars_start_end}-. _"

        self.valid_names = (
            "letters",
            "all-12 to.ge--t_he r",
            "Just cluster namE",
            "Another.clus-ter",
            "endswithdigit4",
            "1startswithdigit",
            "contains_underscore",
        )
        self.invalid_names = (
            "-starts with hyphen",
            ".starts with dot",
            "_starts with underscore",
            "Ends with hyphen-",
            "Ends with dot.",
            "Ends with underscore_",
        ) + tuple(f"forbidden{c}char" for c in set(string.punctuation) - set(self.allowed_name_chars_middle))

        self.bundle = Bundle.objects.create()
        self.prototype = Prototype.objects.create(name="test_prototype_name", type="cluster", bundle=self.bundle)
        self.cluster = Cluster.objects.create(name="test_cluster_name", prototype=self.prototype)

    def test_cluster_update_duplicate_name_fail(self):
        new_cluster = Cluster.objects.create(name="new_name", prototype=self.prototype)
        url = reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk})

        response = self.client.patch(path=url, data={"name": new_cluster.name}, content_type=APPLICATION_JSON)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")
        self.assertEqual(response.json()["desc"], f'Cluster with name "{new_cluster.name}" already exists')

        response = self.client.put(path=url, data={"name": new_cluster.name}, content_type=APPLICATION_JSON)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")
        self.assertEqual(response.json()["desc"], f'Cluster with name "{new_cluster.name}" already exists')

    def test_cluster_create_duplicate_name_fail(self):
        response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={"name": self.cluster.name, "prototype_id": self.cluster.prototype.pk},
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")
        self.assertEqual(response.json()["desc"], f'Cluster with name "{self.cluster.name}" already exists')

    def test_cluster_create_name_validation(self):
        url = reverse(viewname="v1:cluster")
        amount_of_clusters = Cluster.objects.count()
        for name in self.invalid_names:
            with self.subTest("invalid", name=name):
                response = self.client.post(
                    path=url,
                    data={"name": name, "prototype_id": self.prototype.pk},
                    content_type=APPLICATION_JSON,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.json()["code"], "BAD_REQUEST")
                self.assertEqual(Cluster.objects.count(), amount_of_clusters)

        for name in self.valid_names:
            with self.subTest("valid", name=name):
                response = self.client.post(
                    path=url,
                    data={"name": name, "prototype_id": self.prototype.pk},
                    content_type=APPLICATION_JSON,
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.json()["name"], name)

    def test_cluster_update_name_validation(self):
        url = reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk})
        with self.another_user_logged_in(username="admin", password="admin"):
            for name in self.valid_names:
                with self.subTest("correct-patch", name=name):
                    response = self.client.patch(path=url, data={"name": name}, content_type=APPLICATION_JSON)
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertEqual(response.json()["name"], name)

                with self.subTest("correct-put", name=name):
                    response = self.client.put(path=url, data={"name": name}, content_type=APPLICATION_JSON)
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertEqual(response.json()["name"], name)

            for name in self.invalid_names:
                with self.subTest("incorrect-patch", name=name):
                    response = self.client.patch(path=url, data={"name": name}, content_type=APPLICATION_JSON)
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertEqual(response.json()["code"], "BAD_REQUEST")

                with self.subTest("incorrect-put", name=name):
                    response = self.client.put(path=url, data={"name": name}, content_type=APPLICATION_JSON)
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertEqual(response.json()["code"], "BAD_REQUEST")

    def test_cluster_name_update_in_different_states(self):
        url = reverse(viewname="v1:cluster-details", kwargs={"cluster_id": self.cluster.pk})

        self.cluster.state = "created"
        self.cluster.save(update_fields=["state"])

        with self.another_user_logged_in(username="admin", password="admin"):
            for method in ("patch", "put"):
                response = getattr(self.client, method)(
                    path=url,
                    data={"name": self.valid_names[0]},
                    content_type=APPLICATION_JSON,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.json()["name"], self.valid_names[0])

            self.cluster.state = "another state"
            self.cluster.save()

            for method in ("patch", "put"):
                response = getattr(self.client, method)(
                    path=url,
                    data={"name": self.valid_names[0]},
                    content_type=APPLICATION_JSON,
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
