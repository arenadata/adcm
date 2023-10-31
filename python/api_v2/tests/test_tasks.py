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

from datetime import timedelta
from operator import itemgetter

from api_v2.tests.base import BaseAPITestCase
from cm.job import create_task, get_selector
from cm.models import (
    ADCM,
    Action,
    ActionType,
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    HostProvider,
    JobLog,
    ServiceComponent,
    TaskLog,
)
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from adcm.tests.base import BaseTestCase


class TestTask(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.adcm = ADCM.objects.first()
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm.prototype,
            type=ActionType.JOB,
            state_available="any",
        )
        self.task_1 = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now() + timedelta(days=1),
            action=self.action,
        )
        self.task_2 = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now() + timedelta(days=1),
            action=self.action,
            selector=get_selector(self.adcm, self.action),
        )
        self.job = JobLog.objects.create(
            status="failed",
            start_date=timezone.now() + timedelta(days=1),
            finish_date=timezone.now() + timedelta(days=2),
            action=self.action,
            task=self.task_1,
        )

    def test_task_list_success(self):
        response: Response = self.client.get(path=reverse(viewname="v2:tasklog-list"))
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_task_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:tasklog-detail", kwargs={"pk": self.task_2.pk}),
        )
        task_object = {"type": self.adcm.content_type.name, "id": self.adcm.pk, "name": self.adcm.name}
        self.assertEqual(response.data["id"], self.task_2.pk)
        self.assertEqual(response.data["objects"], [task_object])
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_task_retrieve_not_found_fail(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:tasklog-detail", kwargs={"pk": self.task_2.pk + 10}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_task_log_download_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:tasklog-download", kwargs={"pk": self.task_1.pk})
        )
        self.assertEqual(response.status_code, HTTP_200_OK)


class TestTaskObjects(BaseAPITestCase):  # pylint: disable=too-many-instance-attributes
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_service_to_cluster("service_1", self.cluster_1)
        self.service_2 = self.add_service_to_cluster("service_2", self.cluster_1)

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
