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

from io import BytesIO
from operator import itemgetter
from unittest.mock import patch

from cm.api import delete_service
from cm.converters import model_name_to_core_type
from cm.models import (
    ADCM,
    Action,
    Cluster,
    Component,
    Host,
    HostComponent,
    Provider,
    Service,
    TaskLog,
)
from cm.services.job.action import prepare_task_for_action
from cm.tests.mocks.task_runner import RunTaskMock
from core.job.dto import TaskPayloadDTO
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from api_v2.tests.base import BaseAPITestCase


class TestTask(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.adcm = ADCM.objects.first()
        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        component_1 = Component.objects.filter(service=self.service_1, prototype__name="component_1").first()
        self.cluster_action = Action.objects.filter(name="action", prototype=self.cluster_1.prototype).first()
        self.service_1_action = Action.objects.filter(name="action", prototype=self.service_1.prototype).first()
        component_1_action = Action.objects.filter(name="action_1_comp_1", prototype=component_1.prototype).first()
        cluster_object = CoreObjectDescriptor(id=self.cluster_1.pk, type=ADCMCoreType.CLUSTER)
        self.cluster_task = TaskLog.objects.get(
            id=prepare_task_for_action(
                target=cluster_object,
                orm_owner=self.cluster_1,
                action=self.cluster_action.pk,
                payload=TaskPayloadDTO(),
            ).id
        )
        service_object = CoreObjectDescriptor(id=self.service_1.pk, type=ADCMCoreType.SERVICE)
        self.service_task = TaskLog.objects.get(
            id=prepare_task_for_action(
                target=service_object,
                orm_owner=self.service_1,
                action=self.service_1_action.pk,
                payload=TaskPayloadDTO(),
            ).id
        )
        component_object = CoreObjectDescriptor(id=component_1.pk, type=ADCMCoreType.COMPONENT)
        self.component_task = TaskLog.objects.get(
            id=prepare_task_for_action(
                target=component_object,
                orm_owner=component_1,
                action=component_1_action.pk,
                payload=TaskPayloadDTO(),
            ).id
        )
        self.adcm_task = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )

    def test_task_list_success(self):
        response = (self.client.v2 / "tasks").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 4)

    def test_task_filter_by_job_name(self):
        response = (self.client.v2 / "tasks").get(query={"jobName": "comp"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.component_task.pk)

    def test_task_filter_by_object_name(self):
        response = (self.client.v2 / "tasks").get(query={"objectName": "service_1"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.service_task.pk)

    def test_task_filter_by_job_name_multiple_found_success(self):
        response = (self.client.v2 / "tasks").get(query={"jobName": "action"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)
        tasks = response.json()["results"]
        self.assertEqual(tasks[0]["id"], self.component_task.pk)
        self.assertEqual(tasks[1]["id"], self.service_task.pk)
        self.assertEqual(tasks[2]["id"], self.cluster_task.pk)

    def test_task_filter_by_job_name_and_object_name(self):
        response = (self.client.v2 / "tasks").get(query={"jobName": "action", "objectName": "cluster"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.cluster_task.pk)

    def test_task_retrieve_success(self):
        task_object = {"type": self.cluster_1.content_type.name, "id": self.cluster_1.pk, "name": self.cluster_1.name}

        response = self.client.v2[self.cluster_task].get()

        self.assertEqual(response.data["id"], self.cluster_task.pk)
        self.assertEqual(response.data["objects"], [task_object])
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_task_retrieve_not_found_fail(self):
        response = (self.client.v2 / "tasks" / self.get_non_existent_pk(TaskLog)).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_task_log_download_success(self):
        with patch("api_v2.task.views.get_task_download_archive_file_handler", return_value=BytesIO(b"content")):
            response = self.client.v2[self.cluster_task, "logs", "download"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_adcm_5158_adcm_task_view_for_not_superuser_fail(self):
        self.client.login(username="admin", password="admin")
        response = self.client.v2[self.adcm_task].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = (self.client.v2 / "tasks").get()
        self.assertIn(self.adcm_task.pk, [task["id"] for task in response.json()["results"]])

        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.adcm_task].get()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response = (self.client.v2 / "tasks").get()
        self.assertNotIn(self.adcm_task.pk, [task["id"] for task in response.json()["results"]])

    def test_adcm_4142_visibility_after_object_deletion(self):
        cluster_admin_credentials = self.test_user_credentials
        cluster_admin = self.test_user
        service_admin_credentials = {"username": "service_admin_username", "password": "service_admin_passwo"}
        service_admin = self.create_user(**service_admin_credentials)

        with self.grant_permissions(
            to=cluster_admin, on=self.cluster_1, role_name="Cluster Administrator"
        ) as _, self.grant_permissions(to=service_admin, on=self.service_1, role_name="Service Administrator") as _:
            # run action as service admin (create all permissions we interested in)
            self.client.login(**service_admin_credentials)
            with RunTaskMock() as run_task:
                response = self.client.v2[self.service_1, "actions", self.service_1_action, "run"].post(
                    data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
                )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["id"], run_task.target_task.id)
            self.assertEqual(run_task.target_task.status, "created")

            service_task_pk = response.json()["id"]
            child_job_pk = response.json()["childJobs"][0]["id"]

            task_endpoint = self.client.v2 / "tasks" / service_task_pk
            log_list_endpoint = self.client.v2 / "jobs" / child_job_pk / "logs"

            # check tasklog visibility for cluster admin
            self.client.login(**cluster_admin_credentials)
            cluster_admin_response = task_endpoint.get()
            self.assertEqual(cluster_admin_response.status_code, HTTP_200_OK)

            cluster_admin_response = log_list_endpoint.get()
            self.assertSetEqual({log["type"] for log in cluster_admin_response.json()}, {"stdout", "stderr"})

            # check tasklog visibility for service admin
            self.client.login(**service_admin_credentials)
            service_admin_response = task_endpoint.get()
            self.assertEqual(service_admin_response.status_code, HTTP_200_OK)

            service_admin_response = log_list_endpoint.get()
            self.assertSetEqual({log["type"] for log in service_admin_response.json()}, {"stdout", "stderr"})

            # delete service
            delete_service(service=self.service_1)

            # check tasklog visibility for cluster admin
            self.client.login(**cluster_admin_credentials)
            cluster_admin_response = task_endpoint.get()
            self.assertEqual(cluster_admin_response.status_code, HTTP_200_OK)

            cluster_admin_response = log_list_endpoint.get()
            self.assertSetEqual({log["type"] for log in cluster_admin_response.json()}, {"stdout", "stderr"})

            # check tasklog visibility for service admin
            self.client.login(**service_admin_credentials)
            service_admin_response = task_endpoint.get()
            self.assertEqual(service_admin_response.status_code, HTTP_200_OK)

            service_admin_response = log_list_endpoint.get()
            self.assertSetEqual({log["type"] for log in service_admin_response.json()}, {"stdout", "stderr"})


class TestTaskObjects(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.service_2 = self.add_services_to_cluster(service_names=["service_2"], cluster=self.cluster_1).get()

        self.component_1 = Component.objects.get(service=self.service_1, prototype__name="component_1")

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="just-host")

        self.add_host_to_cluster(self.cluster_1, self.host)
        HostComponent.objects.create(
            cluster=self.cluster_1, host=self.host, service=self.service_1, component=self.component_1
        )

        self.cluster_object = {"id": self.cluster_1.pk, "name": self.cluster_1.display_name, "type": "cluster"}
        self.service_object = {
            "id": self.service_1.pk,
            "name": self.service_1.display_name,
            "type": "service",
        }
        self.component_object = {
            "id": self.component_1.pk,
            "name": self.component_1.display_name,
            "type": "component",
        }

        self.provider_object = {"id": self.provider.pk, "name": self.provider.name, "type": "provider"}
        self.host_object = {"id": self.host.pk, "name": self.host.fqdn, "type": "host"}

    def test_cluster_task_objects_success(self) -> None:
        task = self.create_task(object_=self.cluster_1, action_name="action")
        response = self.client.v2[task].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object])

    def test_service_task_objects_success(self) -> None:
        task = self.create_task(object_=self.service_1, action_name="action")
        response = self.client.v2[task].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.service_object])

    def test_component_task_objects_success(self) -> None:
        task = self.create_task(object_=self.component_1, action_name="action_1_comp_1")
        response = self.client.v2[task].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.component_object, self.service_object])

    def test_provider_task_objects_success(self) -> None:
        task = self.create_task(object_=self.provider, action_name="provider_action")
        response = self.client.v2[task].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.provider_object])

    def test_host_task_objects_success(self) -> None:
        task = self.create_task(object_=self.host, action_name="host_action")
        response = self.client.v2[task].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.host_object, self.provider_object])

    def test_host_task_of_cluster_action_objects_success(self) -> None:
        task = self.create_task(object_=self.cluster_1, action_name="cluster_on_host", host=self.host)
        response = self.client.v2[task].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.host_object])

    def test_host_task_of_service_action_objects_success(self) -> None:
        task = self.create_task(object_=self.service_1, action_name="service_on_host", host=self.host)
        response = self.client.v2[task].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.host_object, self.service_object])

    def test_host_task_of_component_action_objects_success(self) -> None:
        task = self.create_task(object_=self.component_1, action_name="component_on_host", host=self.host)
        response = self.client.v2[task].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.component_object, self.host_object, self.service_object])

    @staticmethod
    def create_task(
        object_: Cluster | Service | Component | Provider | Host | ADCM,
        action_name: str,
        *,
        host: Host | None = None,
    ):
        action = Action.objects.get(name=action_name, prototype=object_.prototype)

        owner = CoreObjectDescriptor(
            id=object_.pk, type=model_name_to_core_type(model_name=object_.__class__.__name__.lower())
        )
        target = CoreObjectDescriptor(id=host.pk, type=ADCMCoreType.HOST) if host else owner

        launch = prepare_task_for_action(target=target, orm_owner=object_, action=action.pk, payload=TaskPayloadDTO())

        return TaskLog.objects.get(id=launch.id)
