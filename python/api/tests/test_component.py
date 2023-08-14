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

from pathlib import Path
from unittest.mock import patch

from cm.models import (
    Action,
    Bundle,
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    MaintenanceMode,
    Prototype,
    ServiceComponent,
)
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from adcm.tests.base import BaseTestCase


class TestComponentAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster = Cluster.objects.create(prototype=cluster_prototype, name="test_cluster")
        service_prototype = Prototype.objects.create(
            bundle=bundle,
            type="service",
            display_name="test_service",
        )
        self.service = ClusterObject.objects.create(prototype=service_prototype, cluster=self.cluster)
        self.component = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=bundle,
                type="component",
                display_name="test_component",
            ),
            cluster=self.cluster,
            service=self.service,
        )
        self.host = Host.objects.create(
            fqdn="test-host",
            prototype=Prototype.objects.create(bundle=bundle, type="host"),
        )

    def test_change_maintenance_mode_wrong_name_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertIn(response.json()["desc"], 'maintenance_mode - "wrong" is not a valid choice.;')

    def test_change_maintenance_mode_on_no_action_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": "ON"},
        )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "ON")
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.ON)

    def test_change_maintenance_mode_on_no_service_issue_success(self):
        bundle = self.upload_and_load_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files/bundle_issue_component.tar",
            ),
        )

        cluster_prototype = Prototype.objects.get(bundle=bundle, type="cluster")
        cluster_response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={"name": "test-cluster", "prototype_id": cluster_prototype.pk},
        )
        cluster = Cluster.objects.get(pk=cluster_response.data["id"])

        service_prototype = Prototype.objects.get(bundle=bundle, type="service")
        service_response: Response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster.pk}),
            data={"prototype_id": service_prototype.pk},
        )
        service = ClusterObject.objects.get(pk=service_response.data["id"])

        component_1 = ServiceComponent.objects.get(service=service, prototype__name="first_component")
        component_2 = ServiceComponent.objects.get(service=service, prototype__name="second_component")

        self.assertTrue(service.concerns.exists())
        self.assertTrue(component_2.concerns.exists())
        self.assertFalse(component_1.concerns.exists())

        response: Response = self.client.post(
            path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": component_2.pk}),
            data={"maintenance_mode": "ON"},
        )

        component_2.refresh_from_db()
        service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "ON")
        self.assertEqual(component_2.maintenance_mode, MaintenanceMode.ON)
        self.assertFalse(service.concerns.exists())

    def test_change_maintenance_mode_on_with_action_success(self):
        HostComponent.objects.create(
            cluster=self.cluster,
            host=self.host,
            service=self.service,
            component=self.component,
        )
        action = Action.objects.create(prototype=self.component.prototype, name=settings.ADCM_TURN_ON_MM_ACTION_NAME)

        with patch("adcm.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": self.component.pk}),
                data={"maintenance_mode": "ON"},
            )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "CHANGING")
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.CHANGING)
        start_task_mock.assert_called_once_with(
            action=action,
            obj=self.component,
            conf={},
            attr={},
            hostcomponent=[],
            hosts=[],
            verbose=False,
        )

    def test_change_maintenance_mode_on_from_on_with_action_fail(self):
        self.component.maintenance_mode = MaintenanceMode.ON
        self.component.save()

        with patch("adcm.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": self.component.pk}),
                data={"maintenance_mode": "ON"},
            )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.ON)
        start_task_mock.assert_not_called()

    def test_change_maintenance_mode_off_no_action_success(self):
        self.component.maintenance_mode = MaintenanceMode.ON
        self.component.save()

        response: Response = self.client.post(
            path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": "OFF"},
        )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "OFF")
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.OFF)

    def test_change_maintenance_mode_off_with_action_success(self):
        self.component.maintenance_mode = MaintenanceMode.ON
        self.component.save()
        HostComponent.objects.create(
            cluster=self.cluster,
            host=self.host,
            service=self.service,
            component=self.component,
        )
        action = Action.objects.create(prototype=self.component.prototype, name=settings.ADCM_TURN_OFF_MM_ACTION_NAME)

        with patch("adcm.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": self.component.pk}),
                data={"maintenance_mode": "OFF"},
            )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "CHANGING")
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.CHANGING)
        start_task_mock.assert_called_once_with(
            action=action,
            obj=self.component,
            conf={},
            attr={},
            hostcomponent=[],
            hosts=[],
            verbose=False,
        )

    def test_change_maintenance_mode_off_to_off_with_action_fail(self):
        self.component.maintenance_mode = MaintenanceMode.OFF
        self.component.save()

        with patch("adcm.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": self.component.pk}),
                data={"maintenance_mode": "OFF"},
            )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.OFF)
        start_task_mock.assert_not_called()

    def test_change_maintenance_mode_changing_now_fail(self):
        self.component.maintenance_mode = MaintenanceMode.CHANGING
        self.component.save()

        response: Response = self.client.post(
            path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": "ON"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        response: Response = self.client.post(
            path=reverse(viewname="v1:component-maintenance-mode", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": MaintenanceMode.OFF},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
