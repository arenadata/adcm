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

import json

from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from adcm.tests.base import BaseTestCase
from audit.models import AuditObject, AuditObjectType
from cm.models import Bundle, Prototype, PrototypeConfig


class TestAuditObjects(BaseTestCase):

    # SET UP

    def setUp(self) -> None:
        super().setUp()
        self.cluster_proto: Prototype = None
        self.service_proto: Prototype = None
        self.component_proto: Prototype = None
        self.provider_proto: Prototype = None
        self.host_proto: Prototype = None
        self._prepare_prototypes()

    def _prepare_prototypes(self):
        cluster_bundle = Bundle.objects.create(name="awesome_cluster")
        provider_bundle = Bundle.objects.create(name="awesome_provider")
        for type_ in ("cluster", "service", "component", "provider", "host"):
            name = f"{type_}_proto"
            proto = Prototype.objects.create(
                type=type_,
                name=name,
                version="2.3",
                bundle=provider_bundle if type_ in {"provider", "host"} else cluster_bundle,
            )
            PrototypeConfig.objects.create(name="param", type="integer", prototype=proto)
            setattr(self, name, proto)
        self.component_proto.parent = self.service_proto
        self.component_proto.save()
        self.host_proto.parent = self.provider_proto
        self.host_proto.save()

    # UTILITIES

    def create_provider_via_api(self, name: str = "Provider") -> Response:
        return self.client.post(
            path=reverse("provider"), data={"prototype_id": self.provider_proto.id, "name": name}
        )

    def create_host_via_api(self, fqdn: str, provider_id: int) -> Response:
        return self.client.post(
            path=reverse("host", args=[provider_id]),
            data={"prototype_id": self.host_proto.id, "fqdn": fqdn},
        )

    def create_cluster_via_api(self, name: str = "Cluster") -> Response:
        return self.client.post(
            path=reverse("cluster"), data={"prototype_id": self.cluster_proto.id, "name": name}
        )

    def _get_id_from_create_response(self, resp: Response) -> int:
        self.assertEqual(resp.status_code, HTTP_201_CREATED)
        return resp.data["id"]

    # TESTS

    def test_cluster_flow(self):
        provider_id = self._get_id_from_create_response(self.create_provider_via_api())
        host_id = self._get_id_from_create_response(
            self.create_host_via_api("test-fqdn", provider_id)
        )

        cluster_id = self._get_id_from_create_response(self.create_cluster_via_api())
        filter_kwargs = dict(object_id=cluster_id, object_type=AuditObjectType.Cluster)
        cluster_ao: AuditObject = AuditObject.objects.filter(**filter_kwargs).first()
        self.assertIsNotNone(cluster_ao)
        self.assertFalse(cluster_ao.is_deleted)

        service_id = self._get_id_from_create_response(
            self.client.post(
                path=reverse("service"),
                data={"cluster_id": cluster_id, "prototype_id": self.service_proto.id},
            )
        )
        resp = self.client.post(
            path=reverse("host", kwargs={"cluster_id": cluster_id}), data={"host_id": host_id}
        )
        self.assertEqual(resp.status_code, HTTP_201_CREATED)
        self.assertEqual(AuditObject.objects.filter(**filter_kwargs).count(), 1)
        cluster_ao.refresh_from_db()
        self.assertFalse(cluster_ao.is_deleted)

        resp = self.client.delete(
            path=reverse(
                "service-details", kwargs={"cluster_id": cluster_id, "service_id": service_id}
            )
        )
        self.assertEqual(resp.status_code, HTTP_204_NO_CONTENT)
        resp = self.client.delete(
            path=reverse("host-details", kwargs={"cluster_id": cluster_id, "host_id": host_id})
        )
        self.assertEqual(resp.status_code, HTTP_204_NO_CONTENT)
        cluster_ao.refresh_from_db()
        self.assertFalse(cluster_ao.is_deleted)

        resp = self.client.delete(path=reverse("cluster-details", args=[cluster_id]))
        self.assertEqual(resp.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(AuditObject.objects.filter(**filter_kwargs).count(), 1)
        cluster_ao.refresh_from_db()
        self.assertTrue(cluster_ao.is_deleted)
        self.assertEqual(AuditObject.objects.filter(is_deleted=True).count(), 1)
        self.assertEqual(AuditObject.objects.count(), 3)

    def test_provider_flow(self):
        provider_id = self._get_id_from_create_response(self.create_provider_via_api())
        host_id = self._get_id_from_create_response(
            self.create_host_via_api("test-fqdn", provider_id)
        )
        self.assertEqual(AuditObject.objects.count(), 2)
        self.assertEqual(AuditObject.objects.filter(is_deleted=True).count(), 0)
        resp = self.client.post(
            reverse("config-history", kwargs={"provider_id": provider_id}),
            data={"config": json.dumps({"param": 42})},
        )
        self.assertEqual(resp.status_code, HTTP_201_CREATED)
        resp = self.client.post(
            reverse("config-history", kwargs={"host_id": host_id}),
            data={"config": json.dumps({"param": 42})},
        )
        self.assertEqual(resp.status_code, HTTP_201_CREATED)
        self.assertEqual(AuditObject.objects.count(), 2)
        self.assertEqual(AuditObject.objects.filter(is_deleted=True).count(), 0)
        resp = self.client.delete(reverse("host-details", args=[host_id]))
        self.assertEqual(resp.status_code, HTTP_204_NO_CONTENT)
        resp = self.client.delete(reverse("provider-details", args=[provider_id]))
        self.assertEqual(resp.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(AuditObject.objects.count(), 2)
        self.assertEqual(AuditObject.objects.filter(is_deleted=True).count(), 2)
