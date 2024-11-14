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

from typing import Iterable
from unittest.mock import patch
from uuid import uuid4

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.hierarchy import Tree
from cm.issue import lock_affected_objects
from cm.models import (
    Bundle,
    Cluster,
    Component,
    Host,
    HostComponent,
    ObjectConfig,
    ObjectType,
    Prototype,
    Service,
)
from cm.services.mapping import change_host_component_mapping
from cm.tests.utils import (
    gen_adcm,
    gen_component,
    gen_host,
    gen_host_component,
    gen_job_log,
    gen_prototype,
    gen_provider,
    gen_service,
    gen_task_log,
)
from core.cluster.types import HostComponentEntry
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_409_CONFLICT,
)


class TestAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_files_dir = self.base_dir / "python" / "cm" / "tests" / "files"
        self.bundle_adh_name = "adh.1.5.tar"
        self.bundle_ssh_name = "ssh.1.0.tar"
        self.cluster = "adh42"
        self.host = "test.host.net"
        self.service = "ZOOKEEPER"
        self.component = "ZOOKEEPER_SERVER"

    def get_service_proto_id(self) -> int | None:
        response: Response = self.client.get(path=reverse(viewname="v1:service-prototype-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)

        for service in response.json()["results"]:
            if service["name"] == self.service:
                return service["id"]

        return None

    def get_component_id(self, cluster_id: int, service_id: int, component_name: str) -> int | None:
        response: Response = self.client.get(
            reverse(viewname="v1:component", kwargs={"cluster_id": cluster_id, "service_id": service_id}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        for comp in response.json():
            if comp["name"] == component_name:
                return comp["id"]

        return None

    def get_cluster_proto_id(self) -> tuple[int, int]:
        response: Response = self.client.get(path=reverse(viewname="v1:cluster-prototype-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)

        return response.json()["results"][0]["bundle_id"], response.json()["results"][0]["id"]

    def get_host_in_cluster(self, fqdn: str, name: str | None = None) -> tuple[int, int, int]:
        name = name or uuid4().hex

        response: Response = self.client.get(path=reverse(viewname="v1:host-prototype-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)

        ssh_bundle_id = response.json()["results"][0]["bundle_id"]
        host_proto = response.json()["results"][0]["id"]

        response: Response = self.client.get(path=reverse(viewname="v1:provider-prototype-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)

        provider_proto = response.json()["results"][0]["id"]

        response: Response = self.client.post(
            path=reverse(viewname="v1:provider"), data={"name": name, "prototype_id": provider_proto}
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        provider_id = response.json()["id"]
        response: Response = self.client.post(
            path=reverse(viewname="v1:host"),
            data={"fqdn": fqdn, "prototype_id": host_proto, "provider_id": provider_id},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_id = response.json()["id"]

        return ssh_bundle_id, provider_id, host_id

    def test_access(self):
        self.client.logout()

        api = [reverse(viewname="v1:cluster"), reverse(viewname="v1:host"), reverse(viewname="v1:tasklog-list")]
        for url in api:
            response: Response = self.client.get(url)

            self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
            self.assertEqual(response.json()["detail"], "Authentication credentials were not provided.")

        for url in api:
            response: Response = self.client.post(url, data={})

            self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
            self.assertEqual(response.json()["detail"], "Authentication credentials were not provided.")

        for url in api:
            response: Response = self.client.put(url, {})

            self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
            self.assertEqual(response.json()["detail"], "Authentication credentials were not provided.")

        for url in api:
            response: Response = self.client.delete(url)

            self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
            self.assertEqual(response.json()["detail"], "Authentication credentials were not provided.")

    def test_schema(self):
        response: Response = self.client.get("/api/v1/schema/")

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_docs(self):
        response: Response = self.client.get("/api/v1/docs/")

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get("/api/v1/docs/md/")

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_cluster(self):
        cluster_name = "test-cluster"
        cluster_url = reverse(viewname="v1:cluster")
        self.upload_and_load_bundle(path=self.test_files_dir / self.bundle_adh_name)
        bundle_id, proto_id = self.get_cluster_proto_id()

        response: Response = self.client.post(cluster_url, {})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["name"], ["This field is required."])

        response: Response = self.client.post(cluster_url, {"name": ""})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["name"], ["This field may not be blank."])

        response: Response = self.client.post(cluster_url, {"name": cluster_name})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["This field is required."])

        response: Response = self.client.post(cluster_url, {"name": cluster_name, "prototype_id": ""})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["A valid integer is required."])

        response: Response = self.client.post(cluster_url, {"name": cluster_name, "prototype_id": "some-string"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["A valid integer is required."])

        response: Response = self.client.post(cluster_url, {"name": cluster_name, "prototype_id": 100500})

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROTOTYPE_NOT_FOUND")

        response: Response = self.client.post(
            cluster_url,
            {"name": cluster_name, "prototype_id": proto_id, "description": ""},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["description"], ["This field may not be blank."])

        response: Response = self.client.post(cluster_url, {"name": cluster_name, "prototype_id": proto_id})

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        cluster_id = response.json()["id"]
        this_cluster_url = reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_id})

        response: Response = self.client.get(this_cluster_url)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["name"], cluster_name)

        response: Response = self.client.post(cluster_url, {"name": cluster_name, "prototype_id": proto_id})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")

        response: Response = self.client.delete(this_cluster_url)

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.get(this_cluster_url)

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "CLUSTER_NOT_FOUND")

        response: Response = self.client.delete(this_cluster_url)

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "CLUSTER_NOT_FOUND")

        response: Response = self.client.delete(
            path=reverse(viewname="v1:bundle-detail", kwargs={"bundle_pk": bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_cluster_patching(self):
        name = "test-cluster"
        cluster_url = reverse(viewname="v1:cluster")

        self.upload_and_load_bundle(path=self.test_files_dir / self.bundle_adh_name)
        bundle_id, proto_id = self.get_cluster_proto_id()

        response: Response = self.client.post(cluster_url, {"name": name, "prototype_id": proto_id})

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        cluster_id = response.json()["id"]
        first_cluster_url = reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_id})

        patched_name = "patched-cluster"

        response: Response = self.client.patch(
            first_cluster_url,
            {"name": patched_name},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["name"], patched_name)

        description = "cluster_description"
        response: Response = self.client.patch(
            first_cluster_url,
            {"name": patched_name, "description": description},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["description"], description)

        response: Response = self.client.post(cluster_url, {"name": name, "prototype_id": proto_id})

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        second_cluster_id = response.json()["id"]
        second_cluster_url = reverse(viewname="v1:cluster-details", kwargs={"cluster_id": second_cluster_id})

        response: Response = self.client.patch(
            second_cluster_url,
            {"name": patched_name},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")

        response: Response = self.client.delete(first_cluster_url)

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.delete(second_cluster_url)

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.delete(
            path=reverse(viewname="v1:bundle-detail", kwargs={"bundle_pk": bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_cluster_host(self):
        host = "test.host.net"
        cluster_url = reverse(viewname="v1:cluster")

        self.upload_and_load_bundle(path=self.test_files_dir / self.bundle_adh_name)
        self.upload_and_load_bundle(path=self.test_files_dir / self.bundle_ssh_name)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()

        response: Response = self.client.post(cluster_url, {"name": self.cluster, "prototype_id": cluster_proto})
        cluster_id = response.json()["id"]
        this_cluster_host_url = reverse(viewname="v1:host", kwargs={"cluster_id": cluster_id})

        ssh_bundle_id, _, host_id = self.get_host_in_cluster(host)

        response: Response = self.client.post(this_cluster_host_url, {})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["desc"], "host_id - This field is required.;")

        response: Response = self.client.post(this_cluster_host_url, {"host_id": 100500})

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response: Response = self.client.post(this_cluster_host_url, {"host_id": host_id})

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()["id"], host_id)
        self.assertEqual(response.json()["cluster_id"], cluster_id)

        response: Response = self.client.post(cluster_url, {"name": "qwe", "prototype_id": cluster_proto})
        cluster_id2 = response.json()["id"]
        second_cluster_host_url = reverse(viewname="v1:host", kwargs={"cluster_id": cluster_id2})

        response: Response = self.client.post(second_cluster_host_url, {"host_id": host_id})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "FOREIGN_HOST")

        response: Response = self.client.post(this_cluster_host_url, {"host_id": host_id})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_CONFLICT")

        response: Response = self.client.delete(f"{this_cluster_host_url}{str(host_id)}/")

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.post(second_cluster_host_url, {"host_id": host_id})

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()["cluster_id"], cluster_id2)

        self.client.delete(path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_id}))
        self.client.delete(path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_id2}))
        self.client.delete(path=reverse(viewname="v1:host-details", kwargs={"host_id": host_id}))
        response: Response = self.client.delete(
            path=reverse(viewname="v1:bundle-detail", kwargs={"bundle_pk": adh_bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.delete(
            path=reverse(viewname="v1:bundle-detail", kwargs={"bundle_pk": ssh_bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "BUNDLE_CONFLICT")

    def test_service(self):
        self.upload_and_load_bundle(path=self.test_files_dir / self.bundle_adh_name)
        service_id = self.get_service_proto_id()
        service_url = reverse(viewname="v1:service-prototype-list")
        this_service_url = reverse(viewname="v1:service-prototype-detail", kwargs={"prototype_pk": service_id})

        response: Response = self.client.post(service_url, {})

        self.assertEqual(response.status_code, HTTP_405_METHOD_NOT_ALLOWED)

        response: Response = self.client.get(this_service_url)

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.put(this_service_url, {}, content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_405_METHOD_NOT_ALLOWED)

        response: Response = self.client.delete(this_service_url)

        self.assertEqual(response.status_code, HTTP_405_METHOD_NOT_ALLOWED)

        response: Response = self.client.get(this_service_url)

        self.assertEqual(response.status_code, HTTP_200_OK)

        bundle_id = response.json()["bundle_id"]

        response: Response = self.client.delete(
            path=reverse(viewname="v1:bundle-detail", kwargs={"bundle_pk": bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_cluster_service(self):
        self.upload_and_load_bundle(path=self.test_files_dir / self.bundle_adh_name)

        service_proto_id = self.get_service_proto_id()
        bundle_id, cluster_proto_id = self.get_cluster_proto_id()

        cluster = "test-cluster"
        cluster_url = reverse(viewname="v1:cluster")
        response: Response = self.client.post(cluster_url, {"name": cluster, "prototype_id": cluster_proto_id})

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        cluster_id = response.json()["id"]
        this_service_url = reverse(viewname="v1:service", kwargs={"cluster_id": cluster_id})

        response: Response = self.client.post(
            this_service_url,
            {"prototype_id": "some-string"},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["prototype_id"], ["A valid integer is required."])

        response: Response = self.client.post(
            this_service_url,
            {
                "prototype_id": -1 * service_proto_id,
            },
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROTOTYPE_NOT_FOUND")

        response: Response = self.client.post(
            this_service_url,
            {
                "prototype_id": service_proto_id,
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        service_id = response.json()["id"]

        response: Response = self.client.post(
            this_service_url,
            {
                "prototype_id": service_proto_id,
            },
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "SERVICE_CONFLICT")

        this_service_from_cluster_url = reverse(
            viewname="v1:service-details",
            kwargs={"cluster_id": cluster_id, "service_id": service_id},
        )
        response: Response = self.client.delete(this_service_from_cluster_url)

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.delete(
            path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_id})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.delete(
            path=reverse(viewname="v1:bundle-detail", kwargs={"bundle_pk": bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_hostcomponent(self):
        self.upload_and_load_bundle(path=self.test_files_dir / self.bundle_adh_name)
        self.upload_and_load_bundle(path=self.test_files_dir / self.bundle_ssh_name)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()
        ssh_bundle_id, _, host_id = self.get_host_in_cluster(self.host)
        service_proto_id = self.get_service_proto_id()
        response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={"name": self.cluster, "prototype_id": cluster_proto},
        )
        cluster_id = response.json()["id"]

        response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster_id}),
            data={"prototype_id": service_proto_id},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        service_id = response.json()["id"]

        hc_url = reverse(viewname="v1:host-component", kwargs={"cluster_id": cluster_id})
        response = self.client.post(hc_url, {"hc": {}}, content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")
        self.assertEqual(response.json()["desc"], "hc field is required")

        comp_id = self.get_component_id(cluster_id, service_id, self.component)
        response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": 100500, "component_id": comp_id}]},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": host_id, "component_id": 100500}]},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "COMPONENT_NOT_FOUND")

        response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": host_id, "component_id": comp_id}]},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": cluster_id}),
            data={"host_id": host_id},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.post(
            hc_url,
            {"hc": {"host_id": host_id, "component_id": comp_id}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")
        self.assertEqual(response.json()["desc"], "hc field should be a list")

        response = self.client.post(
            hc_url,
            {"hc": [{"component_id": comp_id}]},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")

        response = self.client.post(hc_url, {"hc": [{"host_id": host_id}]}, content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")

        response = self.client.post(
            hc_url,
            {
                "hc": [
                    {"service_id": service_id, "host_id": 1, "component_id": comp_id},
                    {"service_id": service_id, "host_id": 1, "component_id": comp_id},
                ],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["code"], "INVALID_INPUT")
        self.assertEqual(response.json()["desc"][0:9], "duplicate")

        response: Response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": host_id, "component_id": comp_id}]},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        hs_id = response.json()[0]["id"]

        response: Response = self.client.get(f"{hc_url}{str(hs_id)}/")

        self.assertEqual(response.status_code, HTTP_200_OK)

        zclient_id = self.get_component_id(cluster_id, service_id, "ZOOKEEPER_CLIENT")
        response: Response = self.client.post(
            hc_url,
            {"hc": [{"service_id": service_id, "host_id": host_id, "component_id": zclient_id}]},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={"name": "qwe", "prototype_id": cluster_proto},
            content_type=APPLICATION_JSON,
        )
        cluster_id2 = response.json()["id"]

        response: Response = self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": cluster_id2}),
            data={"hc": [{"service_id": service_id, "host_id": host_id, "component_id": comp_id}]},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "COMPONENT_NOT_FOUND")

        response: Response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster_id2}),
            data={"prototype_id": service_proto_id},
            content_type=APPLICATION_JSON,
        )
        service_id2 = response.json()["id"]

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        comp_id2 = self.get_component_id(cluster_id2, service_id2, self.component)
        response: Response = self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": cluster_id2}),
            data={"hc": [{"service_id": service_id2, "host_id": host_id, "component_id": comp_id2}]},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "HOST_NOT_FOUND")

        response: Response = self.client.delete(f"{hc_url}{str(hs_id)}/")

        self.assertEqual(response.status_code, HTTP_405_METHOD_NOT_ALLOWED)

        self.client.delete(path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_id}))
        self.client.delete(path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_id2}))
        self.client.delete(path=reverse(viewname="v1:host-details", kwargs={"host_id": host_id}))
        response: Response = self.client.delete(
            path=reverse(viewname="v1:bundle-detail", kwargs={"bundle_pk": adh_bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.delete(
            path=reverse(viewname="v1:bundle-detail", kwargs={"bundle_pk": ssh_bundle_id})
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "BUNDLE_CONFLICT")

    def test_config(self):
        self.upload_and_load_bundle(path=self.test_files_dir / self.bundle_adh_name)
        adh_bundle_id, proto_id = self.get_cluster_proto_id()
        service_proto_id = self.get_service_proto_id()
        response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"), data={"name": self.cluster, "prototype_id": proto_id}
        )
        cluster_id = response.json()["id"]

        response: Response = self.client.get(path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster_id}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json(), [])

        response: Response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster_id}),
            data={"prototype_id": 100500},
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["code"], "PROTOTYPE_NOT_FOUND")

        response: Response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster_id}),
            data={"prototype_id": service_proto_id},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        service_id = response.json()["id"]

        zurl = reverse(viewname="v1:service-details", kwargs={"cluster_id": cluster_id, "service_id": service_id})
        response: Response = self.client.get(zurl)

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(
                viewname="v1:config-current",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": "current",
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        id1 = response.json()["id"]
        config = response.json()["config"]

        self.assertEqual(config["zoo.cfg"]["autopurge.purgeInterval"], 24)

        config_history_url = reverse(
            viewname="v1:config-history",
            kwargs={"cluster_id": cluster_id, "service_id": service_id, "object_type": "service"},
        )
        response: Response = self.client.post(path=config_history_url, data={"config": "qwe"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["config"], ["Value must be valid JSON."])

        response: Response = self.client.post(config_history_url, {"config": 42})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["desc"], "Fields `config` and `attr` should be objects when specified")

        config["zoo.cfg"]["autopurge.purgeInterval"] = 42
        config["zoo.cfg"]["port"] = 80
        response: Response = self.client.post(config_history_url, {"config": config}, content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        id2 = response.json()["id"]

        response: Response = self.client.get(
            path=reverse(
                viewname="v1:config-history-version",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": id2,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        config = response.json()["config"]

        self.assertEqual(config["zoo.cfg"]["autopurge.purgeInterval"], 42)

        response: Response = self.client.patch(
            path=reverse(
                viewname="v1:config-history-version-restore",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": id1,
                },
            ),
            data={"description": "New config"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(
                viewname="v1:config-current",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": "current",
                },
            ),
        )
        config = response.json()["config"]

        self.assertEqual(config["zoo.cfg"]["autopurge.purgeInterval"], 24)

        response: Response = self.client.get(
            path=reverse(
                viewname="v1:config-previous",
                kwargs={
                    "cluster_id": cluster_id,
                    "service_id": service_id,
                    "object_type": "service",
                    "version": "previous",
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        config = response.json()["config"]

        self.assertEqual(config["zoo.cfg"]["autopurge.purgeInterval"], 42)

        response: Response = self.client.get(config_history_url)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

        self.client.delete(path=reverse(viewname="v1:cluster-details", kwargs={"cluster_id": cluster_id}))
        self.client.delete(path=reverse(viewname="v1:bundle-detail", kwargs={"bundle_pk": adh_bundle_id}))


class TestAPI2(BaseTestCase):
    def setUp(self):
        gen_adcm()
        self.bundle = Bundle.objects.create(
            name="ADB",
            version="2.5",
            version_order=4,
            edition="community",
            hash="2232f33c6259d44c23046fce4382f16c450f8ba5",
            description="",
            date=timezone.now(),
        )

        common_proto_data = {
            "version": "2.5",
            "license": "absent",
            "license_path": None,
            "license_hash": None,
            "version_order": 11,
            "required": False,
            "shared": False,
            "adcm_min_version": None,
            "monitoring": "active",
            "description": "",
        }
        self.cluster_prototype = Prototype.objects.create(
            bundle_id=self.bundle.id,
            type=ObjectType.CLUSTER,
            name="ADB",
            **common_proto_data,
        )
        self.service_prototype = Prototype.objects.create(
            bundle_id=self.bundle.id,
            type=ObjectType.SERVICE,
            name="some_service",
            **common_proto_data,
        )
        self.component_prototype = Prototype.objects.create(
            bundle_id=self.bundle.id,
            type=ObjectType.COMPONENT,
            name="some_component",
            **common_proto_data,
        )

        self.object_config = ObjectConfig.objects.create(current=0, previous=0)

        self.cluster = Cluster.objects.create(
            prototype_id=self.cluster_prototype.id,
            name="Fear Limpopo",
            description="",
            config_id=self.object_config.id,
            state="installed",
        )

    def save_hc(self, cluster: Cluster, hc_list: Iterable[tuple[Service, Host, Component]]) -> list[HostComponent]:
        change_host_component_mapping(
            cluster_id=cluster.id,
            bundle_id=cluster.bundle_id,
            flat_mapping=(
                HostComponentEntry(host_id=host.id, component_id=component.id) for (_, host, component) in hc_list
            ),
        )
        return list(HostComponent.objects.filter(cluster=cluster))

    @patch("cm.services.mapping.reset_hc_map")
    def test_save_hc(self, mock_reset_hc_map):
        cluster_object = Service.objects.create(prototype=self.service_prototype, cluster=self.cluster)
        host = Host.objects.create(prototype=self.cluster_prototype, cluster=self.cluster)
        component = Prototype.objects.create(
            parent=self.component_prototype,
            type="component",
            bundle_id=self.bundle.id,
            name="node",
        )
        service_component = Component.objects.create(
            cluster=self.cluster,
            service=cluster_object,
            prototype=component,
        )

        HostComponent.objects.create(
            cluster=self.cluster,
            host=host,
            service=cluster_object,
            component=service_component,
        )

        host_comp_list = [(cluster_object, host, service_component)]
        hc_list = self.save_hc(self.cluster, host_comp_list)

        self.assertListEqual(hc_list, [HostComponent.objects.first()])

        mock_reset_hc_map.assert_called_once()

    @patch("cm.services.status.notify.reset_hc_map")
    @patch("cm.api.update_hierarchy_issues")
    def test_save_hc__big_update__locked_hierarchy(
        self,
        mock_issue,  # noqa: ARG002
        mock_load,  # noqa: ARG002
    ):
        """
        Update bigger HC map - move `component_2` from `host_2` to `host_3`
        On locked hierarchy (from ansible task)
        Test:
            host_1 remains the same
            host_2 is unlocked
            host_3 became locked
        """
        service = gen_service(self.cluster)
        component_1_prototype = gen_prototype(
            bundle=self.cluster.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_1"
        )
        component_1 = gen_component(service=service, prototype=component_1_prototype)
        component_2_prototype = gen_prototype(
            bundle=self.cluster.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_2"
        )
        component_2 = gen_component(service=service, prototype=component_2_prototype)
        provider = gen_provider()
        host_1 = gen_host(provider, cluster=self.cluster)
        host_2 = gen_host(provider, cluster=self.cluster)
        host_3 = gen_host(provider, cluster=self.cluster)
        gen_host_component(component_1, host_1)
        gen_host_component(component_2, host_2)

        task = gen_task_log(service)
        gen_job_log(task)
        tree = Tree(self.cluster)
        affected = (node.value for node in tree.get_all_affected(tree.built_from))
        lock_affected_objects(task=task, objects=affected)

        # refresh due to new instances were updated in task.lock_affected()
        host_1.refresh_from_db()
        host_2.refresh_from_db()
        host_3.refresh_from_db()

        self.assertTrue(host_1.locked)
        self.assertTrue(host_2.locked)
        self.assertFalse(host_3.locked)

        new_hc_list = [
            (service, host_1, component_1),
            (service, host_3, component_2),
        ]
        self.save_hc(self.cluster, new_hc_list)

        # refresh due to new instances were updated in save_hc()
        host_1.refresh_from_db()
        host_2.refresh_from_db()
        host_3.refresh_from_db()

        self.assertTrue(host_1.locked)
        self.assertFalse(host_2.locked)
        self.assertTrue(host_3.locked)

    @patch("cm.services.status.notify.reset_hc_map")
    @patch("cm.api.update_hierarchy_issues")
    def test_save_hc__big_update__unlocked_hierarchy(self, mock_update, mock_load):  # noqa: ARG001, ARG002
        """
        Update bigger HC map - move `component_2` from `host_2` to `host_3`
        On unlocked hierarchy (from API)
        Test:
            host_1 remains unlocked
            host_2 remains unlocked
            host_3 remains unlocked
        """
        service = gen_service(self.cluster)
        component_1_prototype = gen_prototype(
            bundle=self.cluster.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_1"
        )
        component_1 = gen_component(service=service, prototype=component_1_prototype)
        component_2_prototype = gen_prototype(
            bundle=self.cluster.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_2"
        )
        component_2 = gen_component(service=service, prototype=component_2_prototype)
        provider = gen_provider()
        host_1 = gen_host(provider, cluster=self.cluster)
        host_2 = gen_host(provider, cluster=self.cluster)
        host_3 = gen_host(provider, cluster=self.cluster)
        gen_host_component(component_1, host_1)
        gen_host_component(component_2, host_2)

        host_1.refresh_from_db()
        host_2.refresh_from_db()
        host_3.refresh_from_db()

        self.assertFalse(host_1.locked)
        self.assertFalse(host_2.locked)
        self.assertFalse(host_3.locked)

        new_hc_list = [
            (service, host_1, component_1),
            (service, host_3, component_2),
        ]
        self.save_hc(self.cluster, new_hc_list)

        # refresh due to new instances were updated in save_hc()
        host_1.refresh_from_db()
        host_2.refresh_from_db()
        host_3.refresh_from_db()

        self.assertFalse(host_1.locked)
        self.assertFalse(host_2.locked)
        self.assertFalse(host_3.locked)
