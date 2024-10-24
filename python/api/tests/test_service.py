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

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import (
    Action,
    Bundle,
    Cluster,
    ClusterBind,
    ClusterObject,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    Prototype,
    ServiceComponent,
)
from cm.services.job.action import ActionRunPayload
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
)


class TestServiceAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.cluster_prototype = Prototype.objects.create(bundle=self.bundle, type="cluster")
        self.cluster = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster")
        self.service_prototype = Prototype.objects.create(
            bundle=self.bundle,
            type="service",
            display_name="test_service",
        )
        self.service = ClusterObject.objects.create(prototype=self.service_prototype, cluster=self.cluster)
        self.component = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="component",
                display_name="test_component",
            ),
            cluster=self.cluster,
            service=self.service,
        )

    def get_host(self, bundle_path: str):
        provider_bundle = self.upload_and_load_bundle(
            path=Path(self.base_dir, bundle_path),
        )
        provider_prototype = Prototype.objects.get(bundle=provider_bundle, type="provider")
        provider_response: Response = self.client.post(
            path=reverse(viewname="v1:provider"),
            data={"name": "test_provider", "prototype_id": provider_prototype.pk},
        )
        provider = HostProvider.objects.get(pk=provider_response.data["id"])

        host_response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"provider_id": provider.pk}),
            data={"fqdn": "test-host"},
        )

        return Host.objects.get(pk=host_response.data["id"])

    def get_cluster(self, bundle_path: str):
        cluster_bundle = self.upload_and_load_bundle(path=Path(self.base_dir, bundle_path))
        cluster_prototype = Prototype.objects.get(bundle_id=cluster_bundle.pk, type="cluster")
        cluster_response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={"name": "test-cluster", "prototype_id": cluster_prototype.pk},
        )

        return Cluster.objects.get(pk=cluster_response.data["id"])

    def test_change_maintenance_mode_wrong_name_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertIn(response.json()["desc"], 'maintenance_mode - "wrong" is not a valid choice.;')

    def test_change_maintenance_mode_on_no_action_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": "ON"},
        )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "ON")
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.ON)

    def test_change_maintenance_mode_on_with_action_success(self):
        HostComponent.objects.create(
            cluster=self.cluster,
            host=self.get_host(bundle_path="python/api/tests/files/bundle_test_provider.tar"),
            service=self.service,
            component=self.component,
        )
        action = Action.objects.create(prototype=self.service.prototype, name=settings.ADCM_TURN_ON_MM_ACTION_NAME)

        with patch("cm.services.maintenance_mode.run_action") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
                data={"maintenance_mode": "ON"},
            )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "CHANGING")
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.CHANGING)
        start_task_mock.assert_called_once_with(action=action, obj=self.service, payload=ActionRunPayload())

    def test_change_maintenance_mode_on_from_on_with_action_fail(self):
        self.service.maintenance_mode = MaintenanceMode.ON
        self.service.save()

        with patch("cm.services.job.action.run_action") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
                data={"maintenance_mode": "ON"},
            )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.ON)
        start_task_mock.assert_not_called()

    def test_change_maintenance_mode_off_no_action_success(self):
        self.service.maintenance_mode = MaintenanceMode.ON
        self.service.save()

        response: Response = self.client.post(
            path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": "OFF"},
        )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "OFF")
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.OFF)

    def test_change_maintenance_mode_off_with_action_success(self):
        self.service.maintenance_mode = MaintenanceMode.ON
        self.service.save()
        HostComponent.objects.create(
            cluster=self.cluster,
            host=self.get_host(bundle_path="python/api/tests/files/bundle_test_provider.tar"),
            service=self.service,
            component=self.component,
        )
        action = Action.objects.create(prototype=self.service.prototype, name=settings.ADCM_TURN_OFF_MM_ACTION_NAME)

        with patch("cm.services.maintenance_mode.run_action") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
                data={"maintenance_mode": "OFF"},
            )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "CHANGING")
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.CHANGING)
        start_task_mock.assert_called_once_with(action=action, obj=self.service, payload=ActionRunPayload())

    def test_change_maintenance_mode_off_to_off_with_action_fail(self):
        self.service.maintenance_mode = MaintenanceMode.OFF
        self.service.save()

        with patch("cm.services.job.action.run_action") as start_task_mock:
            response: Response = self.client.post(
                path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
                data={"maintenance_mode": "OFF"},
            )

        self.service.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.OFF)
        start_task_mock.assert_not_called()

    def test_change_maintenance_mode_changing_now_fail(self):
        self.service.maintenance_mode = MaintenanceMode.CHANGING
        self.service.save()

        response: Response = self.client.post(
            path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": "ON"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        response: Response = self.client.post(
            path=reverse(viewname="v1:service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": "OFF"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_delete_without_action(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_delete_with_action(self):
        action = Action.objects.create(prototype=self.service.prototype, name=settings.ADCM_DELETE_SERVICE_ACTION_NAME)

        with patch("cm.services.service.delete_service"), patch("cm.services.service.run_action") as start_task_mock:
            response: Response = self.client.delete(
                path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
            )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        start_task_mock.assert_not_called()

        host = Host.objects.create(
            fqdn="test-fqdn",
            prototype=Prototype.objects.create(bundle=self.bundle, type="host"),
            provider=HostProvider.objects.create(
                name="test_provider",
                prototype=Prototype.objects.create(bundle=self.bundle, type="provider"),
            ),
        )
        service_component = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="component",
            ),
            cluster=self.cluster,
            service=self.service,
        )
        HostComponent.objects.create(
            cluster=self.cluster,
            host=host,
            service=self.service,
            component=service_component,
        )

        with patch("cm.services.service.delete_service"), patch("cm.services.service.run_action") as start_task_mock:
            response: Response = self.client.delete(
                path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
            )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        start_task_mock.assert_called_once_with(action=action, obj=self.service, payload=ActionRunPayload())

    def test_delete_with_action_not_created_state(self):
        action = Action.objects.create(prototype=self.service.prototype, name=settings.ADCM_DELETE_SERVICE_ACTION_NAME)
        self.service.state = "not created"
        self.service.save(update_fields=["state"])

        with patch("cm.services.service.delete_service"), patch("cm.services.service.run_action") as start_task_mock:
            response: Response = self.client.delete(
                path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
            )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        start_task_mock.assert_called_once_with(action=action, obj=self.service, payload=ActionRunPayload())

    def test_upload_with_cyclic_requires(self):
        self.upload_and_load_bundle(path=Path(self.base_dir, "python/api/tests/files/bundle_cluster_requires.tar"))

    def test_delete_required_fail(self):
        self.service.prototype.required = True
        self.service.prototype.save(update_fields=["required"])

        with patch("cm.services.service.delete_service"):
            response: Response = self.client.delete(
                path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_delete_export_bind_fail(self):
        cluster_2 = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_2")
        service_2 = ClusterObject.objects.create(prototype=self.service_prototype, cluster=cluster_2)
        ClusterBind.objects.create(
            cluster=cluster_2,
            service=service_2,
            source_cluster=self.cluster,
            source_service=self.service,
        )

        with patch("cm.services.service.delete_service"):
            response: Response = self.client.delete(
                path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_delete_import_bind_success(self):
        cluster_2 = Cluster.objects.create(prototype=self.cluster_prototype, name="test_cluster_2")
        service_2 = ClusterObject.objects.create(prototype=self.service_prototype, cluster=cluster_2)
        ClusterBind.objects.create(
            cluster=self.cluster,
            service=self.service,
            source_cluster=cluster_2,
            source_service=service_2,
        )

        with patch("cm.services.service.delete_service"):
            response: Response = self.client.delete(
                path=reverse(viewname="v1:service-details", kwargs={"service_id": self.service.pk}),
            )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_delete_with_dependent_component_fail(self):
        host = self.get_host(bundle_path="python/api/tests/files/bundle_test_provider.tar")
        cluster = self.get_cluster(bundle_path="python/api/tests/files/with_action_dependent_component.tar")
        self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": cluster.pk}),
            data={"host_id": host.pk},
        )

        service_with_component_prototype = Prototype.objects.get(name="with_component", type="service")
        service_with_component_response: Response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster.pk}),
            data={"prototype_id": service_with_component_prototype.pk},
        )
        service_with_component = ClusterObject.objects.get(pk=service_with_component_response.data["id"])

        service_with_dependent_component_prototype = Prototype.objects.get(
            name="with_dependent_component",
            type="service",
        )
        service_with_dependent_component_response: Response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster.pk}),
            data={"prototype_id": service_with_dependent_component_prototype.pk},
        )
        service_with_dependent_component = ClusterObject.objects.get(
            pk=service_with_dependent_component_response.data["id"],
        )

        component = ServiceComponent.objects.get(service=service_with_component)
        component_with_dependent_component = ServiceComponent.objects.get(service=service_with_dependent_component)

        self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": cluster.pk}),
            data={
                "hc": [
                    {"service_id": service_with_component.pk, "component_id": component.pk, "host_id": host.pk},
                    {
                        "service_id": service_with_dependent_component.pk,
                        "component_id": component_with_dependent_component.pk,
                        "host_id": host.pk,
                    },
                ],
            },
            content_type=APPLICATION_JSON,
        )

        response: Response = self.client.delete(
            path=reverse(viewname="v1:service-details", kwargs={"service_id": service_with_component.pk}),
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        HostComponent.objects.all().delete()

        response: Response = self.client.delete(
            path=reverse(viewname="v1:service-details", kwargs={"service_id": service_with_dependent_component.pk}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
