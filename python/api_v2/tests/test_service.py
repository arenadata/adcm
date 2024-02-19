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

from typing import NamedTuple
from unittest.mock import patch

from cm.job import ActionRunPayload, run_action
from cm.models import (
    Action,
    ADCMEntityStatus,
    Cluster,
    ClusterObject,
    ConcernType,
    HostComponent,
    JobLog,
    MaintenanceMode,
    ObjectType,
    Prototype,
    ServiceComponent,
    TaskLog,
)
from cm.services.status.client import FullStatusMap
from django.urls import reverse
from rbac.services.user import create_user
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class FakePopenResponse(NamedTuple):
    pid: int


class TestServiceAPI(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.service_2 = self.add_services_to_cluster(service_names=["service_2"], cluster=self.cluster_1).get()
        self.action = Action.objects.filter(prototype=self.service_2.prototype).first()

    def test_list_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_adcm_4544_list_service_name_ordering_success(self):
        service_3 = self.add_services_to_cluster(service_names=["service_3_manual_add"], cluster=self.cluster_1).get()
        service_list = [self.service_1.display_name, self.service_2.display_name, service_3.display_name]
        response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"ordering": "displayName"},
        )

        self.assertListEqual(
            [service["displayName"] for service in response.json()["results"]],
            service_list,
        )

        response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"ordering": "-displayName"},
        )

        self.assertListEqual(
            [service["displayName"] for service in response.json()["results"]],
            service_list[::-1],
        )

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_2.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.service_2.pk)
        self.assertEqual(response.json()["description"], self.service_2.description)

    def test_delete_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_2.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(ClusterObject.objects.filter(pk=self.service_2.pk).exists())

    def test_delete_failed(self):
        self.service_2.state = "non_created"
        self.service_2.save(update_fields=["state"])

        response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_2.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertTrue(ClusterObject.objects.filter(pk=self.service_2.pk).exists())

    def test_create_success(self):
        initial_service_count = ClusterObject.objects.count()
        manual_add_service_proto = Prototype.objects.get(type=ObjectType.SERVICE, name="service_3_manual_add")

        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"prototypeId": manual_add_service_proto.pk}],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["prototype"]["id"], manual_add_service_proto.pk)

        self.assertEqual(ClusterObject.objects.count(), initial_service_count + 1)

    def test_add_one_success(self):
        initial_service_count = ClusterObject.objects.count()
        manual_add_service_proto = Prototype.objects.get(type=ObjectType.SERVICE, name="service_3_manual_add")

        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"prototypeId": manual_add_service_proto.pk},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["prototype"]["id"], manual_add_service_proto.pk)

        self.assertEqual(ClusterObject.objects.count(), initial_service_count + 1)

    def test_create_wrong_data_fail(self):
        initial_service_count = ClusterObject.objects.count()
        manual_add_service_proto = Prototype.objects.get(type=ObjectType.SERVICE, name="service_3_manual_add")

        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"somekey": manual_add_service_proto.pk},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(ClusterObject.objects.count(), initial_service_count)

    def test_filter_by_name_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"name": "service_1"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_by_display_name_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"display_name": "vice_1"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_by_status_success(self):
        status_map = FullStatusMap(
            clusters={
                str(self.cluster_1.pk): {
                    "status": 16,
                    "hosts": {},
                    "services": {
                        str(self.service_1.pk): {"status": 16, "components": {}, "details": []},
                        str(self.service_2.pk): {"status": 0, "components": {}, "details": []},
                    },
                }
            }
        )

        with patch("api_v2.filters.retrieve_status_map", return_value=status_map):
            response = self.client.get(
                path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
                data={"status": ADCMEntityStatus.UP},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["id"], self.service_2.pk)

    def test_limit_offset_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"limit": 1, "offset": 1},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_change_mm(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_2.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_action_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-action-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_2.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_action_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-action-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_2.pk,
                    "pk": self.action.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_action_run_success(self):
        with patch("cm.job.run_task", return_value=None):
            response = self.client.post(
                path=reverse(
                    viewname="v2:service-action-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_2.pk,
                        "pk": self.action.pk,
                    },
                ),
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)


class TestServiceDeleteAction(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_to_delete, *_ = self.add_services_to_cluster(
            service_names=["service_6_delete_with_action"], cluster=self.cluster_1
        )
        self.service_regular_action: Action = Action.objects.get(
            prototype=self.service_to_delete.prototype, name="regular_action"
        )
        self.cluster_regular_action: Action = Action.objects.get(prototype=self.cluster_1.prototype, name="action")
        HostComponent.objects.create(
            cluster=self.cluster_1,
            service=self.service_to_delete,
            component=ServiceComponent.objects.get(service=self.service_to_delete, prototype__name="component"),
            host=self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="doesntmatter"),
        )

    def test_delete_service_do_not_abort_cluster_actions_fail(self) -> None:
        self.imitate_task_running(action=self.cluster_regular_action, object_=self.cluster_1)

        self.assertTrue(self.service_to_delete.concerns.filter(type=ConcernType.LOCK).exists())

        with patch("subprocess.Popen", return_value=FakePopenResponse(3)), patch("os.kill", return_type=None):
            response = self.client.delete(
                path=reverse(
                    viewname="v2:service-detail",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_to_delete.pk},
                )
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "LOCK_ERROR")

    def test_delete_service_abort_own_actions_success(self) -> None:
        self.imitate_task_running(action=self.service_regular_action, object_=self.service_to_delete)

        self.assertTrue(self.service_to_delete.concerns.filter(type=ConcernType.LOCK).exists())

        with patch("subprocess.Popen", return_value=FakePopenResponse(3)), patch("os.kill", return_type=None):
            response = self.client.delete(
                path=reverse(
                    viewname="v2:service-detail",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_to_delete.pk},
                )
            )
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    @staticmethod
    def imitate_task_running(action: Action, object_: Cluster | ClusterObject) -> TaskLog:
        with patch("subprocess.Popen", return_value=FakePopenResponse(4)):
            task = run_action(action=action, obj=object_, payload=ActionRunPayload(), hosts=[])

        job = JobLog.objects.filter(task=task).first()
        job.status = "running"
        job.save(update_fields=["status"])

        task.status = "running"
        task.pid = 4
        task.save(update_fields=["status", "pid"])

        return task


class TestServiceMaintenanceMode(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1_cl_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1_s_1_cl1 = ServiceComponent.objects.filter(
            cluster_id=self.cluster_1.pk, service_id=self.service_1_cl_1.pk
        ).last()
        self.service_cl_2 = self.add_services_to_cluster(service_names=["service"], cluster=self.cluster_2).get()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

    def test_change_mm_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_1_cl_1.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_adcm_5277_change_mm_service_service_administrator_success(self):
        with self.grant_permissions(to=self.test_user, on=self.service_1_cl_1, role_name="Service Administrator"):
            response = self.client.post(
                path=reverse(
                    viewname="v2:service-maintenance-mode",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_1_cl_1.pk},
                ),
                data={"maintenance_mode": MaintenanceMode.ON},
            )
            self.service_1_cl_1.refresh_from_db()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(self.service_1_cl_1.maintenance_mode, MaintenanceMode.ON)

    def test_adcm_5277_change_mm_component_service_administrator_success(self):
        with self.grant_permissions(to=self.test_user, on=self.service_1_cl_1, role_name="Service Administrator"):
            response = self.client.post(
                path=reverse(
                    "v2:component-maintenance-mode",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1_cl_1.pk,
                        "pk": self.component_1_s_1_cl1.pk,
                    },
                ),
                data={"maintenance_mode": MaintenanceMode.ON},
            )
            self.component_1_s_1_cl1.refresh_from_db()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(self.component_1_s_1_cl1.maintenance_mode, MaintenanceMode.ON)

    def test_change_mm_not_available_fail(self):
        response = self.client.post(
            path=reverse(
                "v2:service-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_2.pk, "pk": self.service_cl_2.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "MAINTENANCE_MODE_NOT_AVAILABLE",
                "level": "error",
                "desc": "Service does not support maintenance mode",
            },
        )


class TestServicePermissions(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="doesntmatter", cluster=self.cluster_1)
        self.host_with_component = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="doesntmatter_2", cluster=self.cluster_1
        )
        component = ServiceComponent.objects.filter(cluster_id=self.cluster_1.pk, service_id=self.service.pk).last()
        self.add_hostcomponent_map(
            cluster=self.cluster_1,
            hc_map=[
                {
                    "host_id": self.host_with_component.pk,
                    "service_id": self.service.pk,
                    "component_id": component.pk,
                }
            ],
        )

    def test_adcm_5278_cluster_hosts_restriction_by_service_administrator_ownership_success(self):
        response_list = self.client.get(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        response_detail = self.client.get(
            path=reverse(
                viewname="v2:host-cluster-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_with_component.pk},
            ),
        )

        self.assertEqual(response_list.status_code, HTTP_200_OK)
        self.assertEqual(response_list.json()["count"], 2)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service, role_name="Service Administrator"):
            response = self.client.get(
                path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertDictEqual(response_list.json()["results"][1], response.json()["results"][0])

            response = self.client.get(
                path=reverse(
                    viewname="v2:host-cluster-detail",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_with_component.pk},
                ),
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertDictEqual(response_detail.json(), response.json())

    def test_adcm_5278_hosts_restriction_by_service_administrator_ownership_success(self):
        response_list = self.client.get(
            path=reverse(viewname="v2:host-list"),
        )

        response_detail = self.client.get(
            path=reverse(
                viewname="v2:host-detail",
                kwargs={"pk": self.host_with_component.pk},
            ),
        )

        self.assertEqual(response_list.status_code, HTTP_200_OK)
        self.assertEqual(response_list.json()["count"], 2)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service, role_name="Service Administrator"):
            response = self.client.get(
                path=reverse(viewname="v2:host-list"),
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertDictEqual(response_list.json()["results"][1], response.json()["results"][0])

            response = self.client.get(
                path=reverse(
                    viewname="v2:host-detail",
                    kwargs={"pk": self.host_with_component.pk},
                ),
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertDictEqual(response_detail.json(), response.json())
