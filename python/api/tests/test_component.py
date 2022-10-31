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

from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from adcm.tests.base import BaseTestCase
from cm.models import (
    Action,
    Bundle,
    Cluster,
    ClusterObject,
    MaintenanceMode,
    Prototype,
    ServiceComponent,
)


class TestComponentAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        cluster = Cluster.objects.create(prototype=cluster_prototype, name="test_cluster")
        service_prototype = Prototype.objects.create(
            bundle=bundle,
            type="service",
            display_name="test_service",
        )
        service = ClusterObject.objects.create(prototype=service_prototype, cluster=cluster)
        component_prototype = Prototype.objects.create(
            bundle=bundle,
            type="component",
            display_name="test_component",
        )
        self.component = ServiceComponent.objects.create(
            prototype=component_prototype,
            cluster=cluster,
            service=service,
        )

    def test_change_maintenance_mode_wrong_name_fail(self):
        response: Response = self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertIn("maintenance_mode", response.data)

    def test_change_maintenance_mode_on_no_action_success(self):
        response: Response = self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.ON)

    def test_change_maintenance_mode_on_with_action_success(self):
        action = Action.objects.create(
            prototype=self.component.prototype, name="turn_on_maintenance_mode"
        )

        with patch("api.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(
                    "component-maintenance-mode", kwargs={"component_id": self.component.pk}
                ),
                data={"maintenance_mode": MaintenanceMode.ON},
            )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.CHANGING)
        start_task_mock.assert_called_once_with(
            action=action, obj=self.component, conf={}, attr={}, hc=[], hosts=[], verbose=False
        )

    def test_change_maintenance_mode_on_from_on_with_action_success(self):
        self.component.maintenance_mode = MaintenanceMode.ON
        self.component.save()

        with patch("api.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(
                    "component-maintenance-mode", kwargs={"component_id": self.component.pk}
                ),
                data={"maintenance_mode": MaintenanceMode.ON},
            )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.ON)
        start_task_mock.assert_not_called()

    def test_change_maintenance_mode_off_no_action_success(self):
        self.component.maintenance_mode = MaintenanceMode.ON
        self.component.save()

        response: Response = self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": MaintenanceMode.OFF},
        )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.OFF)

    def test_change_maintenance_mode_off_with_action_success(self):
        self.component.maintenance_mode = MaintenanceMode.ON
        self.component.save()
        action = Action.objects.create(
            prototype=self.component.prototype, name="turn_off_maintenance_mode"
        )

        with patch("api.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(
                    "component-maintenance-mode", kwargs={"component_id": self.component.pk}
                ),
                data={"maintenance_mode": MaintenanceMode.OFF},
            )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.CHANGING)
        start_task_mock.assert_called_once_with(
            action=action, obj=self.component, conf={}, attr={}, hc=[], hosts=[], verbose=False
        )

    def test_change_maintenance_mode_off_to_off_with_action_success(self):
        self.component.maintenance_mode = MaintenanceMode.OFF
        self.component.save()

        with patch("api.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(
                    "component-maintenance-mode", kwargs={"component_id": self.component.pk}
                ),
                data={"maintenance_mode": MaintenanceMode.OFF},
            )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.OFF)
        start_task_mock.assert_not_called()

    def test_change_maintenance_mode_changing_now_fail(self):
        self.component.maintenance_mode = MaintenanceMode.CHANGING
        self.component.save()

        response: Response = self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "Component maintenance mode is changing now")

        response: Response = self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": MaintenanceMode.OFF},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "Component maintenance mode is changing now")
