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

# Since this module is beyond QA responsibility we will not fix docstrings here
# pylint: disable=missing-function-docstring, missing-class-docstring

import os
import string
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from rest_framework import status

from adcm.tests.base import TestBase


class TestAPI(TestBase):  # pylint: disable=too-many-public-methods
    def setUp(self) -> None:
        super().setUp()
        self.files_dir = os.path.join(settings.BASE_DIR, "python", "cm", "tests", "files")
        self.bundle_adh_name = "adh.1.5.tar"
        self.bundle_ssh_name = "ssh.1.0.tar"
        self.cluster = "adh42"
        self.host = "test.host.net"
        self.service = "ZOOKEEPER"
        self.component = "ZOOKEEPER_SERVER"

    def get_service_proto_id(self):
        response = self.client.get(reverse("service-type"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for service in response.json():
            if service["name"] == self.service:
                return service["id"]
        raise RuntimeError

    def get_component_id(self, cluster_id, service_id, component_name):
        response = self.client.get(
            reverse("component", kwargs={"cluster_id": cluster_id, "service_id": service_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for comp in response.json():
            if comp["name"] == component_name:
                return comp["id"]
        raise RuntimeError

    def get_cluster_proto_id(self):
        response = self.client.get(reverse("cluster-type"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for cluster in response.json():
            return cluster["bundle_id"], cluster["id"]

    def get_host_proto_id(self):
        response = self.client.get(reverse("host-type"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for host in response.json():
            return (host["bundle_id"], host["id"])

    def get_host_provider_proto_id(self):
        response = self.client.get(reverse("provider-type"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for provider in response.json():
            return (provider["bundle_id"], provider["id"])

    def create_host(self, fqdn, name=None):
        name = name or uuid4().hex
        ssh_bundle_id, host_proto = self.get_host_proto_id()
        _, provider_proto = self.get_host_provider_proto_id()
        response = self.client.post(
            reverse("provider"), {"name": name, "prototype_id": provider_proto}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        provider_id = response.json()["id"]
        response = self.client.post(
            reverse("host"), {"fqdn": fqdn, "prototype_id": host_proto, "provider_id": provider_id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        host_id = response.json()["id"]
        return ssh_bundle_id, provider_id, host_id

    def test_access(self):
        api = [reverse("cluster"), reverse("host"), reverse("job"), reverse("task")]
        for url in api:
            response = self.client_unauthorized.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertEqual(
                response.json()["detail"], "Authentication credentials were not provided."
            )

        for url in api:
            response = self.client_unauthorized.post(url, data={})
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertEqual(
                response.json()["detail"], "Authentication credentials were not provided."
            )

        for url in api:
            response = self.client_unauthorized.put(url, {})
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertEqual(
                response.json()["detail"], "Authentication credentials were not provided."
            )

        for url in api:
            response = self.client_unauthorized.delete(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertEqual(
                response.json()["detail"], "Authentication credentials were not provided."
            )

    def test_schema(self):
        response = self.client.get("/api/v1/schema/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_docs(self):
        response = self.client.get("/api/v1/docs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get("/api/v1/docs/md/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cluster(self):  # pylint: disable=too-many-statements
        cluster_name = "test_cluster"
        cluster_url = reverse("cluster")
        self.load_bundle(self.bundle_adh_name)
        bundle_id, proto_id = self.get_cluster_proto_id()

        response = self.client.post(cluster_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["name"], ["This field is required."])

        response = self.client.post(cluster_url, {"name": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["name"], ["This field may not be blank."])

        response = self.client.post(cluster_url, {"name": cluster_name})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["This field is required."])

        response = self.client.post(cluster_url, {"name": cluster_name, "prototype_id": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["A valid integer is required."])

        response = self.client.post(
            cluster_url, {"name": cluster_name, "prototype_id": "some-string"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["A valid integer is required."])

        response = self.client.post(cluster_url, {"name": cluster_name, "prototype_id": 100500})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROTOTYPE_NOT_FOUND")

        response = self.client.post(
            cluster_url,
            {"name": cluster_name, "prototype_id": proto_id, "description": ""},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["description"], ["This field may not be blank."])

        response = self.client.post(cluster_url, {"name": cluster_name, "prototype_id": proto_id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cluster_id = response.json()["id"]
        this_cluster_url = reverse("cluster-details", kwargs={"cluster_id": cluster_id})

        response = self.client.get(this_cluster_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], cluster_name)

        response = self.client.post(cluster_url, {"name": cluster_name, "prototype_id": proto_id})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")

        response = self.client.put(this_cluster_url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.json()["detail"], "Method \"PUT\" not allowed.")

        response = self.client.delete(this_cluster_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(this_cluster_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "CLUSTER_NOT_FOUND")

        response = self.client.delete(this_cluster_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "CLUSTER_NOT_FOUND")

        response = self.client.delete(reverse("bundle-details", kwargs={"bundle_id": bundle_id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cluster_patching(self):
        name = "test_cluster"
        cluster_url = reverse("cluster")

        self.load_bundle(self.bundle_adh_name)
        bundle_id, proto_id = self.get_cluster_proto_id()

        with transaction.atomic():
            response = self.client.post(cluster_url, {"name": name, "prototype_id": proto_id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        cluster_id = response.json()["id"]
        first_cluster_url = reverse("cluster-details", kwargs={"cluster_id": cluster_id})

        patched_name = "patched_cluster"
        with transaction.atomic():
            response = self.client.patch(
                first_cluster_url, {"name": patched_name}, content_type="application/json"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], patched_name)

        description = "cluster_description"
        with transaction.atomic():
            response = self.client.patch(
                first_cluster_url,
                {"name": patched_name, "description": description},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["description"], description)

        with transaction.atomic():
            response = self.client.post(cluster_url, {"name": name, "prototype_id": proto_id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        second_cluster_id = response.json()["id"]
        second_cluster_url = reverse("cluster-details", kwargs={"cluster_id": second_cluster_id})

        with transaction.atomic():
            response = self.client.patch(
                second_cluster_url, {"name": patched_name}, content_type="application/json"
            )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")

        with transaction.atomic():
            response = self.client.delete(first_cluster_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with transaction.atomic():
            response = self.client.delete(second_cluster_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with transaction.atomic():
            response = self.client.delete(
                reverse("bundle-details", kwargs={"bundle_id": bundle_id})
            )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_host(self):  # pylint: disable=too-many-statements
        host = "test.server.net"
        host_url = reverse("host")

        self.load_bundle(self.bundle_ssh_name)
        ssh_bundle_id, host_proto = self.get_host_proto_id()

        response = self.client.post(host_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["fqdn"], ["This field is required."])

        response = self.client.post(
            host_url, {"fqdn": host, "prototype_id": host_proto, "provider_id": 0}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROVIDER_NOT_FOUND")

        _, provider_proto = self.get_host_provider_proto_id()
        response = self.client.post(
            reverse("provider"), {"name": "DF1", "prototype_id": provider_proto}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        provider_id = response.json()["id"]

        response = self.client.post(
            host_url, {"fqdn": host, "prototype_id": 42, "provider_id": provider_id}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROTOTYPE_NOT_FOUND")

        response = self.client.post(host_url, {"fqdn": host, "provider_id": provider_id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["This field is required."])

        response = self.client.post(host_url, {"fqdn": host, "prototype_id": host_proto})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["provider_id"], ["This field is required."])

        response = self.client.post(
            host_url,
            {
                "fqdn": "x" + "deadbeef" * 32,  # 257 chars
                "prototype_id": host_proto,
                "provider_id": provider_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["desc"], "Host name is too long. Max length is 256")

        response = self.client.post(
            host_url,
            {
                "fqdn": "x" + string.punctuation,
                "prototype_id": host_proto,
                "provider_id": provider_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "WRONG_NAME")

        response = self.client.post(
            host_url, {"fqdn": host, "prototype_id": host_proto, "provider_id": provider_id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        host_id = response.json()["id"]

        this_host_url = reverse("host-details", kwargs={"host_id": host_id})

        response = self.client.get(this_host_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["fqdn"], host)

        response = self.client.put(this_host_url, {}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "prototype_id": ["This field is required."],
                "provider_id": ["This field is required."],
                "fqdn": ["This field is required."],
                "maintenance_mode": ["This field is required."],
            },
        )

        response = self.client.post(
            host_url, {"fqdn": host, "prototype_id": host_proto, "provider_id": provider_id}
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_CONFLICT")

        response = self.client.delete(this_host_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(this_host_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response = self.client.delete(this_host_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response = self.client.delete(
            reverse("bundle-details", kwargs={"bundle_id": ssh_bundle_id})
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "BUNDLE_CONFLICT")

        response = self.client.delete(
            reverse("provider-details", kwargs={"provider_id": provider_id})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.delete(
            reverse("bundle-details", kwargs={"bundle_id": ssh_bundle_id})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cluster_host(self):
        host = "test.host.net"
        cluster_url = reverse("cluster")

        self.load_bundle(self.bundle_adh_name)
        self.load_bundle(self.bundle_ssh_name)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()

        response = self.client.post(
            cluster_url, {"name": self.cluster, "prototype_id": cluster_proto}
        )
        cluster_id = response.json()["id"]
        this_cluster_host_url = reverse("host", kwargs={"cluster_id": cluster_id})

        ssh_bundle_id, _, host_id = self.create_host(host)

        response = self.client.post(this_cluster_host_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["host_id"], ["This field is required."])

        response = self.client.post(this_cluster_host_url, {"host_id": 100500})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response = self.client.post(this_cluster_host_url, {"host_id": host_id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["id"], host_id)
        self.assertEqual(response.json()["cluster_id"], cluster_id)

        response = self.client.post(cluster_url, {"name": "qwe", "prototype_id": cluster_proto})
        cluster_id2 = response.json()["id"]
        second_cluster_host_url = reverse("host", kwargs={"cluster_id": cluster_id2})

        response = self.client.post(second_cluster_host_url, {"host_id": host_id})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "FOREIGN_HOST")

        response = self.client.post(this_cluster_host_url, {"host_id": host_id})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_CONFLICT")

        response = self.client.delete(this_cluster_host_url + str(host_id) + "/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.post(second_cluster_host_url, {"host_id": host_id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["cluster_id"], cluster_id2)

        self.client.delete(reverse("cluster-details", kwargs={"cluster_id": cluster_id}))
        self.client.delete(reverse("cluster-details", kwargs={"cluster_id": cluster_id2}))
        self.client.delete(reverse("host-details", kwargs={"host_id": host_id}))
        response = self.client.delete(
            reverse("bundle-details", kwargs={"bundle_id": adh_bundle_id})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.delete(
            reverse("bundle-details", kwargs={"bundle_id": ssh_bundle_id})
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "BUNDLE_CONFLICT")

    def test_service(self):
        self.load_bundle(self.bundle_adh_name)
        service_id = self.get_service_proto_id()
        service_url = reverse("service-type")
        this_service_url = reverse("service-type-details", kwargs={"prototype_id": service_id})

        response = self.client.post(service_url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.get(this_service_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.put(this_service_url, {}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.delete(this_service_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.get(this_service_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bundle_id = response.json()["bundle_id"]

        response = self.client.delete(reverse("bundle-details", kwargs={"bundle_id": bundle_id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cluster_service(self):
        self.load_bundle(self.bundle_adh_name)

        service_proto_id = self.get_service_proto_id()
        bundle_id, cluster_proto_id = self.get_cluster_proto_id()

        cluster = "test_cluster"
        cluster_url = reverse("cluster")
        response = self.client.post(
            cluster_url, {"name": cluster, "prototype_id": cluster_proto_id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cluster_id = response.json()["id"]
        this_service_url = reverse("service", kwargs={"cluster_id": cluster_id})

        response = self.client.post(
            this_service_url,
            {"prototype_id": "some-string"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["A valid integer is required."])

        response = self.client.post(
            this_service_url,
            {
                "prototype_id": -service_proto_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROTOTYPE_NOT_FOUND")

        response = self.client.post(
            this_service_url,
            {
                "prototype_id": service_proto_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        service_id = response.json()["id"]

        response = self.client.post(
            this_service_url,
            {
                "prototype_id": service_proto_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "SERVICE_CONFLICT")

        this_service_from_cluster_url = reverse(
            "service-details", kwargs={"cluster_id": cluster_id, "service_id": service_id}
        )
        response = self.client.delete(this_service_from_cluster_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.delete(reverse("cluster-details", kwargs={"cluster_id": cluster_id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.delete(reverse("bundle-details", kwargs={"bundle_id": bundle_id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_hostcomponent(self):  # pylint: disable=too-many-statements,too-many-locals
        self.load_bundle(self.bundle_adh_name)
        self.load_bundle(self.bundle_ssh_name)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()
        ssh_bundle_id, _, host_id = self.create_host(self.host)
        service_proto_id = self.get_service_proto_id()
        response = self.client.post(
            reverse("cluster"), {"name": self.cluster, "prototype_id": cluster_proto}
        )
        cluster_id = response.json()["id"]

        response = self.client.post(
            reverse("service", kwargs={"cluster_id": cluster_id}),
            {"prototype_id": service_proto_id},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        service_id = response.json()["id"]

        hc_url = reverse("host-component", kwargs={"cluster_id": cluster_id})
        response = self.client.post(hc_url, {"hc": {}}, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")
        self.assertEqual(response.json()["desc"], "hc field is required")

        comp_id = self.get_component_id(cluster_id, service_id, self.component)
        response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": 100500, "component_id": comp_id}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": host_id, "component_id": 100500}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "COMPONENT_NOT_FOUND")

        response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": host_id, "component_id": comp_id}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "FOREIGN_HOST")

        response = self.client.post(
            reverse("host", kwargs={"cluster_id": cluster_id}),
            {"host_id": host_id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            hc_url,
            {"hc": {"host_id": host_id, "component_id": comp_id}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")
        self.assertEqual(response.json()["desc"], "hc field should be a list")

        response = self.client.post(
            hc_url, {"hc": [{"component_id": comp_id}]}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")

        response = self.client.post(
            hc_url, {"hc": [{"host_id": host_id}]}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")

        response = self.client.post(
            hc_url,
            {
                "hc": [
                    {"service_id": service_id, "host_id": 1, "component_id": comp_id},
                    {"service_id": service_id, "host_id": 1, "component_id": comp_id},
                ]
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")
        self.assertEqual(response.json()["desc"][0:9], "duplicate")

        response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": host_id, "component_id": comp_id}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        hs_id = response.json()[0]["id"]

        response = self.client.get(hc_url + str(hs_id) + "/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        zclient_id = self.get_component_id(cluster_id, service_id, "ZOOKEEPER_CLIENT")
        response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": host_id, "component_id": zclient_id}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse("cluster"),
            {"name": "qwe", "prototype_id": cluster_proto},
            content_type="application/json",
        )
        cluster_id2 = response.json()["id"]

        response = self.client.post(
            reverse("host-component", kwargs={"cluster_id": cluster_id2}),
            {"hc": [{"service_id": service_id, "host_id": host_id, "component_id": comp_id}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "CLUSTER_SERVICE_NOT_FOUND")

        response = self.client.post(
            reverse("service", kwargs={"cluster_id": cluster_id2}),
            {"prototype_id": service_proto_id},
            content_type="application/json",
        )
        service_id2 = response.json()["id"]
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        comp_id2 = self.get_component_id(cluster_id2, service_id2, self.component)
        response = self.client.post(
            reverse("host-component", kwargs={"cluster_id": cluster_id2}),
            {"hc": [{"service_id": service_id2, "host_id": host_id, "component_id": comp_id2}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "FOREIGN_HOST")

        response = self.client.delete(hc_url + str(hs_id) + "/")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        self.client.delete(reverse("cluster-details", kwargs={"cluster_id": cluster_id}))
        self.client.delete(reverse("cluster-details", kwargs={"cluster_id": cluster_id2}))
        self.client.delete(reverse("host-details", kwargs={"host_id": host_id}))
        response = self.client.delete(
            reverse("bundle-details", kwargs={"bundle_id": adh_bundle_id})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.delete(
            reverse("bundle-details", kwargs={"bundle_id": ssh_bundle_id})
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "BUNDLE_CONFLICT")

    def test_config(self):  # pylint: disable=too-many-statements
        self.load_bundle(self.bundle_adh_name)
        adh_bundle_id, proto_id = self.get_cluster_proto_id()
        service_proto_id = self.get_service_proto_id()
        response = self.client.post(
            reverse("cluster"), {"name": self.cluster, "prototype_id": proto_id}
        )
        cluster_id = response.json()["id"]

        response = self.client.get(reverse("service", kwargs={"cluster_id": cluster_id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

        response = self.client.post(
            reverse("service", kwargs={"cluster_id": cluster_id}), {"prototype_id": 100500}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROTOTYPE_NOT_FOUND")

        response = self.client.post(
            reverse("service", kwargs={"cluster_id": cluster_id}),
            {"prototype_id": service_proto_id},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        service_id = response.json()["id"]

        zurl = reverse(
            "service-details", kwargs={"cluster_id": cluster_id, "service_id": service_id}
        )
        response = self.client.get(zurl)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            reverse(
                "config-current",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": "current",
                },
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        id1 = response.json()["id"]
        config = response.json()["config"]
        self.assertEqual(config["zoo.cfg"]["autopurge.purgeInterval"], 24)

        config_history_url = reverse(
            "config-history",
            kwargs={"cluster_id": cluster_id, "service_id": service_id, "object_type": "service"},
        )
        response = self.client.post(config_history_url, {"config": "qwe"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["config"], ["Value must be valid JSON."])

        response = self.client.post(config_history_url, {"config": 42})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["desc"], "config should not be just one int or float")

        config["zoo.cfg"]["autopurge.purgeInterval"] = 42
        config["zoo.cfg"]["port"] = 80
        response = self.client.post(
            config_history_url, {"config": config}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        id2 = response.json()["id"]

        response = self.client.get(
            reverse(
                "config-history-version",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": id2,
                },
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        config = response.json()["config"]
        self.assertEqual(config["zoo.cfg"]["autopurge.purgeInterval"], 42)

        response = self.client.patch(
            reverse(
                "config-history-version-restore",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": id1,
                },
            ),
            {"description": "New config"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(
            reverse(
                "config-current",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": "current",
                },
            )
        )
        config = response.json()["config"]
        self.assertEqual(config["zoo.cfg"]["autopurge.purgeInterval"], 24)

        response = self.client.get(
            reverse(
                "config-previous",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": "previous",
                },
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        config = response.json()["config"]
        self.assertEqual(config["zoo.cfg"]["autopurge.purgeInterval"], 42)

        response = self.client.get(config_history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

        self.client.delete(reverse("cluster-details", kwargs={"cluster_id": cluster_id}))
        self.client.delete(reverse("bundle-details", kwargs={"bundle_id": adh_bundle_id}))
