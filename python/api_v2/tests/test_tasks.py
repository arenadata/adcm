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

from api_v2.tests.base import BaseAPITestCase
from cm.job import create_task
from cm.models import (
    ADCM,
    Action,
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    HostProvider,
    ServiceComponent,
    TaskLog,
)
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND


class TestTask(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        component_1 = ServiceComponent.objects.filter(service=service_1, prototype__name="component_1").first()
        self.cluster_action = Action.objects.filter(name="action", prototype=self.cluster_1.prototype).first()
        service_1_action = Action.objects.filter(name="action", prototype=service_1.prototype).first()
        component_1_action = Action.objects.filter(name="action_1_comp_1", prototype=component_1.prototype).first()
        self.cluster_task = create_task(
            action=self.cluster_action,
            obj=self.cluster_1,
            conf={},
            attr={},
            hostcomponent=[],
            hosts=[],
            verbose=False,
            post_upgrade_hc=[],
        )
        self.service_task = create_task(
            action=service_1_action,
            obj=service_1,
            conf={},
            attr={},
            hostcomponent=[],
            hosts=[],
            verbose=False,
            post_upgrade_hc=[],
        )
        self.component_task = create_task(
            action=component_1_action,
            obj=component_1,
            conf={},
            attr={},
            hostcomponent=[],
            hosts=[],
            verbose=False,
            post_upgrade_hc=[],
        )

    def test_task_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:tasklog-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    def test_task_filter_by_job_name(self):
        response = self.client.get(path=reverse(viewname="v2:tasklog-list"), data={"jobName": "comp"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.component_task.pk)

    def test_task_filter_by_object_name(self):
        response = self.client.get(path=reverse(viewname="v2:tasklog-list"), data={"objectName": "service_1"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.service_task.pk)

    def test_task_filter_by_job_name_multiple_found_success(self):
        response = self.client.get(path=reverse(viewname="v2:tasklog-list"), data={"jobName": "action"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)
        tasks = response.json()["results"]
        self.assertEqual(tasks[0]["id"], self.component_task.pk)
        self.assertEqual(tasks[1]["id"], self.service_task.pk)
        self.assertEqual(tasks[2]["id"], self.cluster_task.pk)

    def test_task_filter_by_job_name_and_object_name(self):
        response = self.client.get(
            path=reverse(viewname="v2:tasklog-list"), data={"jobName": "action", "objectName": "cluster"}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.cluster_task.pk)

    def test_task_retrieve_success(self):
        task_object = {"type": self.cluster_1.content_type.name, "id": self.cluster_1.pk, "name": self.cluster_1.name}

        response = self.client.get(
            path=reverse(viewname="v2:tasklog-detail", kwargs={"pk": self.cluster_task.pk}),
        )

        self.assertEqual(response.data["id"], self.cluster_task.pk)
        self.assertEqual(response.data["objects"], [task_object])
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_task_retrieve_not_found_fail(self):
        response = self.client.get(
            path=reverse(viewname="v2:tasklog-detail", kwargs={"pk": self.get_non_existent_pk(TaskLog)}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_task_log_download_success(self):
        with patch("api_v2.task.views.get_task_download_archive_file_handler", return_value=BytesIO(b"content")):
            response = self.client.get(
                path=reverse(viewname="v2:tasklog-download", kwargs={"pk": self.cluster_task.pk})
            )

        self.assertEqual(response.status_code, HTTP_200_OK)


class TestTaskObjects(BaseAPITestCase):  # pylint: disable=too-many-instance-attributes
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.service_2 = self.add_services_to_cluster(service_names=["service_2"], cluster=self.cluster_1).get()

        self.component_1 = ServiceComponent.objects.get(service=self.service_1, prototype__name="component_1")

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
        response = self.client.get(path=reverse("v2:tasklog-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object])

    def test_service_task_objects_success(self) -> None:
        task = self.create_task(object_=self.service_1, action_name="action")
        response = self.client.get(path=reverse("v2:tasklog-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.service_object])

    def test_component_task_objects_success(self) -> None:
        task = self.create_task(object_=self.component_1, action_name="action_1_comp_1")
        response = self.client.get(path=reverse("v2:tasklog-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.component_object, self.service_object])

    def test_provider_task_objects_success(self) -> None:
        task = self.create_task(object_=self.provider, action_name="provider_action")
        response = self.client.get(path=reverse("v2:tasklog-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.provider_object])

    def test_host_task_objects_success(self) -> None:
        task = self.create_task(object_=self.host, action_name="host_action")
        response = self.client.get(path=reverse("v2:tasklog-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.host_object, self.provider_object])

    def test_host_task_of_cluster_action_objects_success(self) -> None:
        task = self.create_task(object_=self.cluster_1, action_name="cluster_on_host", host=self.host)
        response = self.client.get(path=reverse("v2:tasklog-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.host_object])

    def test_host_task_of_service_action_objects_success(self) -> None:
        task = self.create_task(object_=self.service_1, action_name="service_on_host", host=self.host)
        response = self.client.get(path=reverse("v2:tasklog-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.host_object, self.service_object])

    def test_host_task_of_component_action_objects_success(self) -> None:
        task = self.create_task(object_=self.component_1, action_name="component_on_host", host=self.host)
        response = self.client.get(path=reverse("v2:tasklog-detail", kwargs={"pk": task.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)
        objects = sorted(response.json()["objects"], key=itemgetter("type"))
        self.assertEqual(objects, [self.cluster_object, self.component_object, self.host_object, self.service_object])

    @staticmethod
    def create_task(
        object_: Cluster | ClusterObject | ServiceComponent | HostProvider | Host | ADCM,
        action_name: str,
        *,
        host: Host | None = None
    ):
        action = Action.objects.get(name=action_name, prototype=object_.prototype)
        hosts = [] if not host else [host.pk]
        return create_task(
            action=action,
            obj=host or object_,
            conf={},
            attr={},
            hostcomponent=[],
            hosts=hosts,
            verbose=False,
            post_upgrade_hc=[],
        )
