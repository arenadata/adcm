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

import os
import string

from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import Bundle, Cluster, Host, HostProvider, Prototype


class TestHostAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.files_dir = settings.BASE_DIR / "python" / "cm" / "tests" / "files"
        self.bundle_ssh_name = "ssh.1.0.tar"
        self.load_bundle(self.bundle_ssh_name)
        self.provider = HostProvider.objects.create(
            name="test_provider",
            prototype=Prototype.objects.all()[1],
        )
        self.host = Host.objects.create(
            fqdn="test_fqdn",
            prototype=Prototype.objects.all()[0],
            provider=self.provider,
            maintenance_mode="on",
        )

    def load_bundle(self, bundle_name):
        with open(os.path.join(self.files_dir, bundle_name), encoding="utf-8") as f:
            response: Response = self.client.post(
                path=reverse("upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": bundle_name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def get_host_proto_id(self):
        response: Response = self.client.get(reverse("host-type"))

        self.assertEqual(response.status_code, HTTP_200_OK)

        for host in response.json():
            return host["bundle_id"], host["id"]

    def get_host_provider_proto_id(self):
        response: Response = self.client.get(reverse("provider-type"))

        self.assertEqual(response.status_code, HTTP_200_OK)

        for provider in response.json():
            return provider["bundle_id"], provider["id"]

    def test_host(self):  # pylint: disable=too-many-statements
        host = "test.server.net"
        host_url = reverse("host")

        # self.load_bundle(self.bundle_ssh_name)
        ssh_bundle_id, host_proto = self.get_host_proto_id()

        response: Response = self.client.post(host_url, {})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["fqdn"], ["This field is required."])

        response: Response = self.client.post(
            host_url, {"fqdn": host, "prototype_id": host_proto, "provider_id": 0}
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROVIDER_NOT_FOUND")

        _, provider_proto = self.get_host_provider_proto_id()
        response: Response = self.client.post(
            reverse("provider"), {"name": "DF1", "prototype_id": provider_proto}
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        provider_id = response.json()["id"]

        response: Response = self.client.post(
            host_url, {"fqdn": host, "prototype_id": 42, "provider_id": provider_id}
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROTOTYPE_NOT_FOUND")

        response: Response = self.client.post(host_url, {"fqdn": host, "provider_id": provider_id})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["This field is required."])

        response: Response = self.client.post(host_url, {"fqdn": host, "prototype_id": host_proto})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["provider_id"], ["This field is required."])

        response: Response = self.client.post(
            host_url,
            {
                "fqdn": f"x{'deadbeef' * 32}",  # 257 chars
                "prototype_id": host_proto,
                "provider_id": provider_id,
            },
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertIn("fqdn", response.json())

        response: Response = self.client.post(
            host_url,
            {
                "fqdn": f"x{string.punctuation}",
                "prototype_id": host_proto,
                "provider_id": provider_id,
            },
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "WRONG_NAME")

        response: Response = self.client.post(
            host_url, {"fqdn": host, "prototype_id": host_proto, "provider_id": provider_id}
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_id = response.json()["id"]

        this_host_url = reverse("host-details", kwargs={"host_id": host_id})

        response: Response = self.client.get(this_host_url)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["fqdn"], host)

        response: Response = self.client.put(this_host_url, {}, content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "prototype_id": ["This field is required."],
                "provider_id": ["This field is required."],
                "fqdn": ["This field is required."],
                "maintenance_mode": ["This field is required."],
            },
        )

        response: Response = self.client.post(
            host_url, {"fqdn": host, "prototype_id": host_proto, "provider_id": provider_id}
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_CONFLICT")

        response: Response = self.client.delete(this_host_url)

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.get(this_host_url)

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response: Response = self.client.delete(this_host_url)

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response: Response = self.client.delete(
            reverse("bundle-details", kwargs={"bundle_id": ssh_bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "BUNDLE_CONFLICT")

        response: Response = self.client.delete(
            reverse("provider-details", kwargs={"provider_id": provider_id})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.provider.delete()
        response: Response = self.client.delete(
            reverse("bundle-details", kwargs={"bundle_id": ssh_bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_host_update_fqdn_success(self):
        new_test_fqdn = "new_test_fqdn"

        response: Response = self.client.patch(
            path=reverse("host-details", kwargs={"host_id": self.host.pk}),
            data={"fqdn": new_test_fqdn, "maintenance_mode": "on"},
            content_type=APPLICATION_JSON,
        )
        self.host.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.host.fqdn, new_test_fqdn)

    def test_host_update_same_fqdn_success(self):
        self.host.state = "active"
        self.host.save(update_fields=["state"])

        response: Response = self.client.patch(
            path=reverse("host-details", kwargs={"host_id": self.host.pk}),
            data={"fqdn": self.host.fqdn, "maintenance_mode": "on"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_host_update_fqdn_not_created_state_fail(self):
        self.host.state = "active"
        self.host.save(update_fields=["state"])

        response: Response = self.client.patch(
            path=reverse("host-details", kwargs={"host_id": self.host.pk}),
            data={"fqdn": "new_test_fqdn", "maintenance_mode": "on"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_UPDATE_ERROR")

    def test_host_update_fqdn_has_cluster_fail(self):
        self.host.state = "active"
        self.host.save(update_fields=["state"])

        cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(bundle=Bundle.objects.first(), type="cluster"),
            name="test_cluster",
        )
        self.host.state = "active"
        self.host.cluster = cluster
        self.host.save(update_fields=["state", "cluster"])

        response: Response = self.client.patch(
            path=reverse("host-details", kwargs={"host_id": self.host.pk}),
            data={"fqdn": "new_test_fqdn", "maintenance_mode": "on"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_UPDATE_ERROR")

    def test_host_update_wrong_fqdn_fail(self):
        response: Response = self.client.patch(
            path=reverse("host-details", kwargs={"host_id": self.host.pk}),
            data={"fqdn": ".new_test_fqdn", "maintenance_mode": "on"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_CONFLICT")

    def test_host_update_not_created_state_wrong_fqdn_fail(self):
        self.host.state = "active"
        self.host.save(update_fields=["state"])

        response: Response = self.client.patch(
            path=reverse("host-details", kwargs={"host_id": self.host.pk}),
            data={"fqdn": ".new_test_fqdn", "maintenance_mode": "on"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_CONFLICT")
