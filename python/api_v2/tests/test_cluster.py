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

from typing import Callable
from unittest.mock import patch

from api_v2.tests.base import BaseAPITestCase
from cm.models import Action, ADCMEntityStatus, Cluster, TaskLog
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)


class TestCluster(BaseAPITestCase):
    def get_cluster_status_mock(self) -> Callable:
        def inner(cluster: Cluster) -> int:
            if cluster.pk == self.cluster_1.pk:
                return 0

            return 32

        return inner

    def test_list_success(self):
        response: Response = self.client.get(path=reverse(viewname="v2:cluster-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.cluster_1.pk)

    def test_filter_by_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"name": self.cluster_1.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_by_wrong_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"name": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status_up_success(self):
        with patch("api_v2.cluster.filters.get_cluster_status", new_callable=self.get_cluster_status_mock):
            response: Response = self.client.get(
                path=reverse(viewname="v2:cluster-list"),
                data={"status": ADCMEntityStatus.UP},
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_status_down_success(self):
        with patch("api_v2.cluster.filters.get_cluster_status", new_callable=self.get_cluster_status_mock):
            response: Response = self.client.get(
                path=reverse(viewname="v2:cluster-list"),
                data={"status": ADCMEntityStatus.DOWN},
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

    def test_filter_by_prototype_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeDisplayName": self.cluster_1.prototype.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_wrong_prototype_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeDisplayName": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={
                "prototype_id": self.cluster_1.prototype.pk,
                "name": "new_test_cluster",
                "description": "Test cluster description",
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_update_failed(self):
        wrong_cluster_name = "__new_test_cluster_name"
        correct_cluster_name = "new_test_cluster_name"

        response: Response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": wrong_cluster_name},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.cluster_1.state = "not_created"
        self.cluster_1.save(update_fields=["state"])

        response: Response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": correct_cluster_name},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_update_success(self):
        new_test_cluster_name = "new_test_cluster_name"
        response: Response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": new_test_cluster_name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        self.cluster_1.refresh_from_db()

        self.assertEqual(self.cluster_1.name, new_test_cluster_name)

    def test_delete_success(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Cluster.objects.filter(pk=self.cluster_1.pk).exists())

    def test_service_prototypes_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-service-prototypes", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)


class TestClusterActions(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_action = Action.objects.get(prototype=self.cluster_1.prototype, name="action")

    def test_list_cluster_actions_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-action-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_list_cluster_actions_no_actions_cluster_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-action-list", kwargs={"cluster_pk": self.cluster_2.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(response.json(), [])

    def test_list_cluster_actions_wrong_cluster_fail(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:cluster-action-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_cluster_action_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:cluster-action-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_run_cluster_action_success(self):
        tasklog = TaskLog.objects.create(
            object_id=self.cluster_1.pk,
            object_type=ContentType.objects.get(app_label="cm", model="cluster"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
            action=self.cluster_action,
        )

        with patch("api_v2.action.views.start_task", return_value=tasklog):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-action-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action.pk},
                ),
                data={"host_component_map": {}, "config": {}, "attr": {}, "is_verbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
