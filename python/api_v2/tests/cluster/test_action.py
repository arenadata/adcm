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

from unittest.mock import patch

from api_v2.tests.cluster.base import ClusterBaseTestCase
from cm.models import Cluster
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from adcm.tests.base import APPLICATION_JSON


class TestAction(ClusterBaseTestCase):
    def test_list_cluster_actions_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:action-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_list_cluster_actions_no_actions_cluster_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:action-list", kwargs={"cluster_pk": self.cluster_2.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_list_cluster_actions_wrong_cluster_fail(self):
        cluster_pks = Cluster.objects.all().values_list("pk", flat=True).order_by("-pk")
        response: Response = self.client.get(
            path=reverse(viewname="v2:action-list", kwargs={"cluster_pk": cluster_pks[0] + 1}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_cluster_action_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:action-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.action.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_run_cluster_action_success(self):
        with patch("api_v2.action.views.start_task"):
            response: Response = self.client.post(
                path=reverse(viewname="v2:action-run", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.action.pk}),
                data={
                    "host_component_map": [
                        {
                            "id": self.hostcomponent.pk,
                            "host_id": self.host.pk,
                            "component_id": self.component.pk,
                            "service_id": self.service.pk,
                        },
                    ],
                    "config": {"additional_prop_1": {}},
                    "attr": {},
                    "is_verbose": True,
                },
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_list_host_actions_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:action-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "host_pk": self.host.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_retrieve_host_action_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:action-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "host_pk": self.host.pk,
                    "pk": self.action.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_run_host_action_success(self):
        with patch("api_v2.action.views.start_task"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:action-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "host_pk": self.host.pk, "pk": self.action.pk},
                ),
                data={
                    "host_component_map": [
                        {
                            "id": self.hostcomponent.pk,
                            "host_id": self.host.pk,
                            "component_id": self.component.pk,
                            "service_id": self.service.pk,
                        },
                    ],
                    "config": {"additional_prop_1": {}},
                    "attr": {},
                    "is_verbose": True,
                },
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
