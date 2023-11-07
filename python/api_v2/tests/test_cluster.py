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
from cm.models import Action, ADCMEntityStatus, Cluster, ClusterObject, Prototype
from django.urls import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


class TestCluster(BaseAPITestCase):  # pylint:disable=too-many-public-methods
    def get_cluster_status_mock(self) -> Callable:
        def inner(cluster: Cluster) -> int:
            if cluster.pk == self.cluster_1.pk:
                return 0

            return 32

        return inner

    def test_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:cluster-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_adcm_4539_ordering_success(self):
        cluster_3 = self.add_cluster(bundle=self.bundle_1, name="cluster_3", description="cluster_3")
        cluster_4 = self.add_cluster(bundle=self.bundle_2, name="cluster_4", description="cluster_3")
        cluster_list = [self.cluster_1.name, self.cluster_2.name, cluster_3.name, cluster_4.name]
        response = self.client.get(path=reverse(viewname="v2:cluster-list"), data={"ordering": "name"})

        self.assertListEqual([cluster["name"] for cluster in response.json()["results"]], cluster_list)

        response = self.client.get(path=reverse(viewname="v2:cluster-list"), data={"ordering": "-name"})

        self.assertListEqual([cluster["name"] for cluster in response.json()["results"]], cluster_list[::-1])

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.cluster_1.pk)

    def test_filter_by_name_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"name": self.cluster_1.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_by_wrong_name_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"name": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status_up_success(self):
        with patch("api_v2.cluster.filters.get_cluster_status", new_callable=self.get_cluster_status_mock):
            response = self.client.get(
                path=reverse(viewname="v2:cluster-list"),
                data={"status": ADCMEntityStatus.UP},
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_status_down_success(self):
        with patch("api_v2.cluster.filters.get_cluster_status", new_callable=self.get_cluster_status_mock):
            response = self.client.get(
                path=reverse(viewname="v2:cluster-list"),
                data={"status": ADCMEntityStatus.DOWN},
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

    def test_filter_by_prototype_name_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeName": self.cluster_1.prototype.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_wrong_prototype_name_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeName": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_filter_by_prototype_display_name_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeDisplayName": self.cluster_1.prototype.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_wrong_prototype_display_name_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeDisplayName": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={
                "prototype_id": self.cluster_1.prototype.pk,
                "name": "new_test_cluster",
                "description": "Test cluster description",
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_crete_without_required_field_fail(self):
        response = self.client.post(path=reverse(viewname="v2:cluster-list"), data={})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BAD_REQUEST",
                "desc": "prototype_id - This field is required.;name - This field is required.;",
                "level": "error",
            },
        )

    def test_create_without_not_required_field_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototype_id": self.cluster_1.prototype.pk, "name": "new_test_cluster"},
        )

        cluster = Cluster.objects.get(name="new_test_cluster")
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(cluster.description, "")

    def test_create_same_name_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={
                "prototype_id": self.cluster_1.prototype.pk,
                "name": self.cluster_1.name,
                "description": "Test cluster description",
            },
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_update_failed(self):
        wrong_cluster_name = "__new_test_cluster_name"
        correct_cluster_name = "new_test_cluster_name"

        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": wrong_cluster_name},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.cluster_1.state = "not_created"
        self.cluster_1.save(update_fields=["state"])

        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": correct_cluster_name},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_update_success(self):
        new_test_cluster_name = "new_test_cluster_name"
        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": new_test_cluster_name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        self.cluster_1.refresh_from_db()

        self.assertEqual(self.cluster_1.name, new_test_cluster_name)

    def test_delete_success(self):
        response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Cluster.objects.filter(pk=self.cluster_1.pk).exists())

    def test_service_prototypes_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-service-prototypes", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 5)
        self.assertListEqual(
            [prototype["displayName"] for prototype in response.json()],
            [
                "service_1",
                "service_2",
                "service_3_manual_add",
                "service_4_save_config_without_required_field",
                "service_5_variant_type_without_values",
            ],
        )

    def test_service_candidates_success(self):
        self.add_service_to_cluster(service_name="service_3_manual_add", cluster=self.cluster_1)

        response = self.client.get(
            path=reverse(viewname="v2:cluster-service-candidates", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 4)
        self.assertListEqual(
            [prototype["displayName"] for prototype in response.json()],
            [
                "service_1",
                "service_2",
                "service_4_save_config_without_required_field",
                "service_5_variant_type_without_values",
            ],
        )

    def test_service_create_success(self):
        service_prototype = Prototype.objects.filter(type="service").first()
        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"prototype_id": service_prototype.pk}],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()[0]["name"], service_prototype.name)
        self.assertEqual(ClusterObject.objects.get(cluster_id=self.cluster_1.pk).name, "service_1")


class TestClusterActions(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_action = Action.objects.get(prototype=self.cluster_1.prototype, name="action")
        self.cluster_action_with_config = Action.objects.get(prototype=self.cluster_1.prototype, name="with_config")
        self.cluster_action_with_hc = Action.objects.get(prototype=self.cluster_1.prototype, name="with_hc")

    def test_list_cluster_actions_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-action-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)

    def test_list_cluster_actions_no_actions_cluster_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-action-list", kwargs={"cluster_pk": self.cluster_2.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(response.json(), [])

    def test_list_cluster_actions_wrong_cluster_fail(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-action-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_cluster_action_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-action-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_run_cluster_action_success(self):
        with patch("cm.job.run_task", return_value=None):
            response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-action-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action.pk},
                ),
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_run_action_with_config_success(self):
        config = {
            "simple": "kuku",
            "grouped": {"simple": 5, "second": 4.3},
            "after": ["something"],
            "activatable_group": {"text": "text"},
        }
        adcm_meta = {"/activatable_group": {"isActive": True}}

        with patch("cm.job.run_task", return_value=None):
            response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-action-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action_with_config.pk},
                ),
                data={"configuration": {"config": config, "adcmMeta": adcm_meta}},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_run_action_with_config_wrong_configuration_fail(self):
        with patch("cm.job.run_task", return_value=None):
            response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-action-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action_with_config.pk},
                ),
                data={"configuration": []},
            )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BAD_REQUEST",
                "desc": "non_field_errors - Invalid data. Expected a dictionary, but got list.;",
                "level": "error",
            },
        )

    def test_run_action_with_config_required_adcm_meta_fail(self):
        config = {"simple": "kuku", "grouped": {"simple": 5, "second": 4.3}, "after": ["something"]}

        with patch("cm.job.run_task", return_value=None):
            response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-action-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action_with_config.pk},
                ),
                data={"configuration": {"config": config}},
            )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "adcm_meta - This field is required.;", "level": "error"}
        )

    def test_run_action_with_config_required_config_fail(self):
        with patch("cm.job.run_task", return_value=None):
            response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-action-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action_with_config.pk},
                ),
                data={"configuration": {"adcmMeta": {}}},
            )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "config - This field is required.;", "level": "error"}
        )

    def test_retrieve_action_with_hc_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-action-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action_with_hc.pk},
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        hc_map = response.json()["hostComponentMapRules"]
        self.assertEqual(len(hc_map), 2)
        add, remove = sorted(hc_map, key=lambda rec: rec["action"])
        self.assertDictEqual(add, {"action": "add", "component": "component_1", "service": "service_1"})
        self.assertDictEqual(remove, {"action": "remove", "component": "component_2", "service": "service_1"})
