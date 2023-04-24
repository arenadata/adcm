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

from cm.models import MaintenanceMode
from django.urls import reverse
from rbac.tests.test_policy.base import PolicyBaseTestCase
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from adcm.tests.base import APPLICATION_JSON


class PolicyNoRightsUserHaveNoAccessTestCase(PolicyBaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.another_user_log_in(username=self.new_user.username, password=self.new_user_password)

    def test_no_rights_user_have_no_access(self):  # pylint: disable=too-many-statements
        response: Response = self.client.get(
            path=reverse(viewname="cluster-details", kwargs={"cluster_id": self.cluster.pk}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(viewname="service-details", kwargs={"service_id": self.last_service_pk}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(viewname="component-details", kwargs={"component_id": self.last_component_pk}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(viewname="provider-details", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(viewname="host-details", kwargs={"host_id": self.last_host_pk}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(viewname="host", kwargs={"cluster_id": self.cluster.pk}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster", "version": "current"},
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.last_service_pk,
                    "object_type": "service",
                    "version": "current",
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={"component_id": self.last_component_pk, "object_type": "component", "version": "current"},
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={"provider_id": self.provider.pk, "object_type": "provider", "version": "current"},
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.get(
            path=reverse(viewname="object-action", kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster"}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json(), [])

        response: Response = self.client.get(
            path=reverse(
                viewname="object-action", kwargs={"service_id": self.last_service_pk, "object_type": "service"}
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json(), [])

        response: Response = self.client.get(
            path=reverse(
                viewname="object-action", kwargs={"component_id": self.last_component_pk, "object_type": "component"}
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json(), [])

        response: Response = self.client.get(
            path=reverse(viewname="object-action", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json(), [])

        response: Response = self.client.post(
            path=reverse(viewname="host-component", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "cluster_id": self.cluster.pk,
                "hc": [
                    {
                        "component_id": self.last_component_pk,
                        "host_id": self.last_host_pk,
                        "service_id": self.last_service_pk,
                    }
                ],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.post(
            path=reverse(viewname="config-history", kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster"}),
            data={"config": {"float": 3.3}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.last_service_pk, "object_type": "service"},
            ),
            data={"config": {"float": 3.3}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"component_id": self.last_component_pk, "object_type": "component"},
            ),
            data={"config": {"float": 3.3}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        response: Response = self.client.post(
            path=reverse(viewname="config-history", kwargs={"provider_id": self.provider.pk}),
            data={"config": {"string": "new_string"}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"host_id": self.last_host_pk, "object_type": "host"},
            ),
            data={"config": {"string": "new_string"}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"cluster_id": self.cluster.pk, "host_id": self.last_host_pk, "object_type": "host"},
            ),
            data={"attr": {}, "config": {"string": "new_string"}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        response = self.client.post(
            path=reverse(viewname="service", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "prototype_id": self.service_6_proto.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        response = self.client.delete(
            path=reverse(
                viewname="service-details",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.last_service_pk},
            ),
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response = self.client.post(
            path=reverse(viewname="service-maintenance-mode", kwargs={"service_id": self.last_service_pk}),
            data={
                "maintenance_mode": MaintenanceMode.ON,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response = self.client.post(
            path=reverse(viewname="component-maintenance-mode", kwargs={"component_id": self.last_component_pk}),
            data={
                "maintenance_mode": MaintenanceMode.ON,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response = self.client.post(
            path=reverse(viewname="host-maintenance-mode", kwargs={"host_id": self.last_host_pk}),
            data={
                "maintenance_mode": MaintenanceMode.ON,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
