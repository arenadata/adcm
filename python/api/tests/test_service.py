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

from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import (
    Action,
    Bundle,
    Cluster,
    ClusterBind,
    ClusterObject,
    Host,
    HostProvider,
    MaintenanceMode,
    Prototype,
    ServiceComponent,
)


class TestServiceAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        self.cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        self.cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster")
        self.service_prototype = Prototype.objects.create(
            bundle=bundle,
            type="service",
            display_name="test_service",
        )
        self.service = ClusterObject.objects.create(prototype=self.service_prototype, cluster=self.cluster)

    def test_change_maintenance_mode_wrong_name_fail(self):
        response: Response = self.client.post(
            path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertIn("maintenance_mode", response.data)

    def test_change_maintenance_mode_on_no_action_success(self):
        response: Response = self.client.post(
            path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.ON)

    def test_change_maintenance_mode_on_with_action_success(self):
        action = Action.objects.create(prototype=self.service.prototype, name=settings.ADCM_TURN_ON_MM_ACTION_NAME)

        with patch("api.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
                data={"maintenance_mode": MaintenanceMode.ON},
            )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.CHANGING)
        start_task_mock.assert_called_once_with(
            action=action, obj=self.service, conf={}, attr={}, hc=[], hosts=[], verbose=False
        )

    def test_change_maintenance_mode_on_from_on_with_action_success(self):
        self.service.maintenance_mode = MaintenanceMode.ON
        self.service.save()

        with patch("api.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
                data={"maintenance_mode": MaintenanceMode.ON},
            )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.ON)
        start_task_mock.assert_not_called()

    def test_change_maintenance_mode_off_no_action_success(self):
        self.service.maintenance_mode = MaintenanceMode.ON
        self.service.save()

        response: Response = self.client.post(
            path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": MaintenanceMode.OFF},
        )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.OFF)

    def test_change_maintenance_mode_off_with_action_success(self):
        self.service.maintenance_mode = MaintenanceMode.ON
        self.service.save()
        action = Action.objects.create(prototype=self.service.prototype, name=settings.ADCM_TURN_OFF_MM_ACTION_NAME)

        with patch("api.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
                data={"maintenance_mode": MaintenanceMode.OFF},
            )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.CHANGING)
        start_task_mock.assert_called_once_with(
            action=action, obj=self.service, conf={}, attr={}, hc=[], hosts=[], verbose=False
        )

    def test_change_maintenance_mode_off_to_off_with_action_success(self):
        self.service.maintenance_mode = MaintenanceMode.OFF
        self.service.save()

        with patch("api.utils.start_task") as start_task_mock:
            response: Response = self.client.post(
                path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
                data={"maintenance_mode": MaintenanceMode.OFF},
            )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.OFF)
        start_task_mock.assert_not_called()

    def test_change_maintenance_mode_changing_now_fail(self):
        self.service.maintenance_mode = MaintenanceMode.CHANGING
        self.service.save()

        response: Response = self.client.post(
            path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "Service maintenance mode is changing now")

        response: Response = self.client.post(
            path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": MaintenanceMode.OFF},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "Service maintenance mode is changing now")

    def test_delete_without_action(self):
        response: Response = self.client.delete(path=reverse("service-details", kwargs={"service_id": self.service.pk}))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_delete_with_action(self):
        action = Action.objects.create(prototype=self.service.prototype, name=settings.ADCM_DELETE_SERVICE_ACTION_NAME)

        with patch("api.service.views.delete_service"), patch("api.service.views.start_task") as start_task_mock:
            response: Response = self.client.delete(
                path=reverse("service-details", kwargs={"service_id": self.service.pk})
            )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        start_task_mock.assert_called_once_with(
            action=action, obj=self.service, conf={}, attr={}, hc=[], hosts=[], verbose=False
        )

    def test_delete_service_with_requires_fail(self):
        # pylint: disable=too-many-locals

        provider_bundle = self.upload_and_load_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files/bundle_test_provider_concern.tar",
            ),
        )
        cluster_bundle = self.upload_and_load_bundle(
            path=Path(
                settings.BASE_DIR,
                "python/api/tests/files/bundle_cluster_requires.tar",
            ),
        )

        provider_prototype = Prototype.objects.get(bundle=provider_bundle, type="provider")
        provider_response: Response = self.client.post(
            path=reverse("provider"),
            data={"name": "test_provider", "prototype_id": provider_prototype.pk},
        )
        provider = HostProvider.objects.get(pk=provider_response.data["id"])

        host_response: Response = self.client.post(
            path=reverse("host", kwargs={"provider_id": provider.pk}),
            data={"fqdn": "test-host"},
        )
        host = Host.objects.get(pk=host_response.data["id"])

        cluster_prototype = Prototype.objects.get(bundle_id=cluster_bundle.pk, type="cluster")
        cluster_response: Response = self.client.post(
            path=reverse("cluster"),
            data={"name": "test-cluster", "prototype_id": cluster_prototype.pk},
        )
        cluster = Cluster.objects.get(pk=cluster_response.data["id"])

        service_1_prototype = Prototype.objects.get(name="service_1", type="service")
        service_1_response: Response = self.client.post(
            path=reverse("service", kwargs={"cluster_id": cluster.pk}),
            data={"prototype_id": service_1_prototype.pk},
        )
        service_1 = ClusterObject.objects.get(pk=service_1_response.data["id"])

        service_2_prototype = Prototype.objects.get(name="service_2", type="service")
        service_2_response: Response = self.client.post(
            path=reverse("service", kwargs={"cluster_id": cluster.pk}),
            data={"prototype_id": service_2_prototype.pk},
        )
        service_2 = ClusterObject.objects.get(pk=service_2_response.data["id"])

        with patch("api.service.views.delete_service"):
            response: Response = self.client.delete(
                path=reverse("service-details", kwargs={"service_id": service_1.pk})
            )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.client.post(
            path=reverse("host", kwargs={"cluster_id": cluster.pk}),
            data={"host_id": host.pk},
        )

        component_2_1 = ServiceComponent.objects.get(service=service_2, prototype__name="component_1")
        component_1_1 = ServiceComponent.objects.get(service=service_1, prototype__name="component_1")

        self.client.post(
            path=reverse("host-component", kwargs={"cluster_id": cluster.pk}),
            data={
                "hc": [
                    {"service_id": service_2.pk, "component_id": component_2_1.pk, "host_id": host.pk},
                    {"service_id": service_1.pk, "component_id": component_1_1.pk, "host_id": host.pk},
                ]
            },
            content_type=APPLICATION_JSON,
        )

        response: Response = self.client.delete(path=reverse("service-details", kwargs={"service_id": service_1.pk}))

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_delete_required_fail(self):
        self.service.prototype.required = True
        self.service.prototype.save(update_fields=["required"])

        with patch("api.service.views.delete_service"):
            response: Response = self.client.delete(
                path=reverse("service-details", kwargs={"service_id": self.service.pk})
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_delete_bind_fail(self):
        cluster_2 = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_2")
        service_2 = ClusterObject.objects.create(prototype=self.service_prototype, cluster=cluster_2)
        ClusterBind.objects.create(
            cluster=self.cluster, service=self.service, source_cluster=cluster_2, source_service=service_2
        )

        with patch("api.service.views.delete_service"):
            response: Response = self.client.delete(
                path=reverse("service-details", kwargs={"service_id": self.service.pk})
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
