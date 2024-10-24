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

from cm.models import Action, JobLog, LogStorage, ObjectType, Prototype, ServiceComponent
from rest_framework.status import HTTP_200_OK

from api_v2.tests.base import BaseAPITestCase


class TestLogStorage(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_1_action = Action.objects.get(prototype=self.cluster_1.prototype, name="action")
        self.service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1)[0]
        self.service_action = Action.objects.get(prototype=self.service.prototype, name="action")
        self.host = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_1)
        component_prototype = Prototype.objects.get(
            bundle=self.bundle_1, type=ObjectType.COMPONENT, name="component_1", parent=self.service.prototype
        )
        self.component = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service, prototype=component_prototype
        )
        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host, self.component)])
        self.component_action = Action.objects.get(prototype=self.component.prototype, name="action_1_comp_1")

        self.simulate_finished_task(object_=self.cluster_1, action=self.cluster_1_action)
        self.simulate_finished_task(object_=self.component, action=self.component_action)
        self.simulate_finished_task(object_=self.service, action=self.service_action)

        for i, log in enumerate(LogStorage.objects.all()):
            log.name = f"log {i} name"
            log.body = f"log {i} body"
            if i % 3 == 0:
                log.format = "custom"
                log.type = "newtype"
            log.save()

    def test_filtering_success(self):
        log_list_endpoint = self.client.v2 / "jobs" / JobLog.objects.first().pk / "logs"
        logstorage = LogStorage.objects.first()
        filters = {
            "id": (logstorage.pk, None, 0),
            "name": (logstorage.name, logstorage.name[1:-3].upper(), "wrong"),
            "type": (logstorage.type, logstorage.type[1:-3].upper(), "wrong"),
        }
        exact_items_found, partial_items_found = 1, 1
        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            with self.subTest(filter_name=filter_name):
                response = log_list_endpoint.get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(len(response.json()), exact_items_found)

                response = log_list_endpoint.get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(len(response.json()), 0)

                if partial_value:
                    response = log_list_endpoint.get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(len(response.json()), partial_items_found)

    def test_ordering_success(self):
        job_pk = JobLog.objects.first().pk
        log_list_endpoint = self.client.v2 / "jobs" / job_pk / "logs"

        ordering_fields = {
            "id": "id",
            "name": "name",
            "type": "type",
        }

        for model_field, ordering_field in ordering_fields.items():
            with self.subTest(ordering_field=ordering_field):
                response = log_list_endpoint.get(query={"ordering": ordering_field})
                self.assertListEqual(
                    [log[ordering_field] for log in response.json()],
                    list(
                        LogStorage.objects.filter(job__id=job_pk)
                        .order_by(model_field)
                        .values_list(model_field, flat=True)
                    ),
                )

                response = log_list_endpoint.get(query={"ordering": f"-{ordering_field}"})
                self.assertListEqual(
                    [log[ordering_field] for log in response.json()],
                    list(
                        LogStorage.objects.filter(job__id=job_pk)
                        .order_by(f"-{model_field}")
                        .values_list(model_field, flat=True)
                    ),
                )
