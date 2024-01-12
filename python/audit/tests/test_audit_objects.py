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

from adcm.tests.base import BaseTestCase
from cm.models import Bundle, Prototype, PrototypeConfig
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from audit.models import AuditObject, AuditObjectType


class TestAuditObjects(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        cluster_bundle = Bundle.objects.create(name="awesome_cluster")
        provider_bundle = Bundle.objects.create(name="awesome_provider")
        self.cluster_proto = Prototype.objects.create(
            type="cluster",
            name="cluster_proto",
            version="2.3",
            bundle=cluster_bundle,
        )
        PrototypeConfig.objects.create(name="param", type="integer", prototype=self.cluster_proto)
        self.service_proto = Prototype.objects.create(
            type="service",
            name="service_proto",
            version="2.3",
            bundle=cluster_bundle,
        )
        PrototypeConfig.objects.create(name="param", type="integer", prototype=self.service_proto)
        component_proto = Prototype.objects.create(
            type="component",
            name="component_proto",
            version="2.3",
            bundle=cluster_bundle,
        )
        PrototypeConfig.objects.create(name="param", type="integer", prototype=component_proto)
        self.provider_proto = Prototype.objects.create(
            type="provider",
            name="provider_proto",
            version="2.3",
            bundle=provider_bundle,
        )
        PrototypeConfig.objects.create(name="param", type="integer", prototype=self.provider_proto)
        self.host_proto = Prototype.objects.create(
            type="host",
            name="host_proto",
            version="2.3",
            bundle=provider_bundle,
        )
        PrototypeConfig.objects.create(name="param", type="integer", prototype=self.host_proto)
        component_proto.parent = self.service_proto
        component_proto.save(update_fields=["parent"])

    def test_cluster_flow(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:provider"),
            data={"prototype_id": self.provider_proto.id, "name": "Provider"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        provider_id = response.data["id"]

        response: Response = self.client.post(
            path=reverse(viewname="v1:host", args=[provider_id]),
            data={"prototype_id": self.host_proto.id, "fqdn": "test-fqdn"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_id = response.data["id"]

        response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={"prototype_id": self.cluster_proto.id, "name": "Cluster"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        cluster_id = response.data["id"]
        filter_kwargs = {"object_id": cluster_id, "object_type": AuditObjectType.CLUSTER}
        cluster_ao: AuditObject = AuditObject.objects.filter(**filter_kwargs).first()

        self.assertIsNotNone(cluster_ao)
        self.assertFalse(cluster_ao.is_deleted)

        response: Response = self.client.post(
            path=reverse(viewname="v1:service"),
            data={"cluster_id": cluster_id, "prototype_id": self.service_proto.id},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        service_id = response.data["id"]

        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": cluster_id}),
            data={"host_id": host_id},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(AuditObject.objects.filter(**filter_kwargs).count(), 1)

        cluster_ao.refresh_from_db()

        self.assertFalse(cluster_ao.is_deleted)

        response: Response = self.client.delete(
            path=reverse(viewname="v1:service-details", kwargs={"cluster_id": cluster_id, "service_id": service_id}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.delete(
            path=reverse(viewname="v1:host-details", kwargs={"cluster_id": cluster_id, "host_id": host_id}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        cluster_ao.refresh_from_db()

        self.assertFalse(cluster_ao.is_deleted)

        response: Response = self.client.delete(path=reverse(viewname="v1:cluster-details", args=[cluster_id]))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(AuditObject.objects.filter(**filter_kwargs).count(), 1)

        cluster_ao.refresh_from_db()

        self.assertTrue(cluster_ao.is_deleted)
        self.assertEqual(AuditObject.objects.filter(is_deleted=True).count(), 1)
        self.assertEqual(AuditObject.objects.count(), 3)

    def test_provider_flow(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:provider"),
            data={"prototype_id": self.provider_proto.id, "name": "Provider"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        provider_id = response.data["id"]

        response: Response = self.client.post(
            path=reverse(viewname="v1:host", args=[provider_id]),
            data={"prototype_id": self.host_proto.id, "fqdn": "test-fqdn"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_id = response.data["id"]

        self.assertEqual(AuditObject.objects.count(), 2)
        self.assertEqual(AuditObject.objects.filter(is_deleted=True).count(), 0)

        response: Response = self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"provider_id": provider_id}),
            data={"config": json.dumps({"param": 42})},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"host_id": host_id}),
            data={"config": json.dumps({"param": 42})},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(AuditObject.objects.count(), 2)
        self.assertEqual(AuditObject.objects.filter(is_deleted=True).count(), 0)

        response: Response = self.client.delete(path=reverse(viewname="v1:host-details", args=[host_id]))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.delete(path=reverse(viewname="v1:provider-details", args=[provider_id]))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(AuditObject.objects.count(), 2)
        self.assertEqual(AuditObject.objects.filter(is_deleted=True).count(), 2)
