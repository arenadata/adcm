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

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import (
    Action,
    ActionType,
    Bundle,
    Cluster,
    Component,
    Host,
    MaintenanceMode,
    Prototype,
    Provider,
    Service,
    SubAction,
)
from cm.tests.mocks.task_runner import RunTaskMock
from core.types import ADCMCoreType
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT


class TestHostAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.cluster_prototype = Prototype.objects.create(
            bundle=self.bundle,
            type="cluster",
            allow_maintenance_mode=True,
        )
        cluster = Cluster.objects.create(name="test_cluster", prototype=self.cluster_prototype)

        self.provider_prototype = Prototype.objects.create(bundle=self.bundle, type="provider")
        self.host_provider = Provider.objects.create(name="test_provider_2", prototype=self.provider_prototype)

        self.host_prototype = Prototype.objects.create(bundle=self.bundle, type="host")
        self.host = Host.objects.create(
            fqdn="test_host_fqdn",
            prototype=self.host_prototype,
            cluster=cluster,
            provider=self.host_provider,
        )

    def test_change_mm_wrong_name_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertIn(response.json()["desc"], 'maintenance_mode - "wrong" is not a valid choice.;')

    def test_change_mm_to_changing_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": "CHANGING"},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_change_mm_on_no_action_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": "ON"},
        )

        self.host.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "ON")
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.ON)

    def test_change_mm_on_with_action_success(self):
        SubAction.objects.create(
            action=Action.objects.create(
                prototype=self.host.cluster.prototype,
                name=settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME,
                type=ActionType.JOB,
                state_available="any",
                host_action=True,
            ),
            script_type="ansible",
            script="somethign.yaml",
        )

        with RunTaskMock() as run_task:
            response: Response = self.client.post(
                path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
                data={"maintenance_mode": "ON"},
            )

        self.host.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "CHANGING")
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.CHANGING)

        self.assertIsNotNone(run_task.target_task)
        self.assertEqual(run_task.target_task.task_object, self.host)
        self.assertEqual(run_task.target_task.owner_id, self.host.cluster.pk)
        self.assertEqual(run_task.target_task.owner_type, ADCMCoreType.CLUSTER.value)

        run_task.runner.run(run_task.target_task.pk)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        self.host.refresh_from_db()
        # since MM wasn't changed with plugin, rollback will be preformed
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.OFF.value)

    def test_change_mm_on_from_on_with_action_fail(self):
        self.host.maintenance_mode = MaintenanceMode.ON
        self.host.save(update_fields=["maintenance_mode"])

        with RunTaskMock() as run_task:
            response: Response = self.client.post(
                path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
                data={"maintenance_mode": "ON"},
            )

        self.host.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.ON)
        self.assertIsNone(run_task.target_task)

    def test_change_mm_off_no_action_success(self):
        self.host.maintenance_mode = MaintenanceMode.ON
        self.host.save(update_fields=["maintenance_mode"])

        response: Response = self.client.post(
            path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": "OFF"},
        )

        self.host.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "OFF")
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.OFF)

    def test_change_mm_off_with_action_success(self):
        self.host.maintenance_mode = MaintenanceMode.ON
        self.host.save(update_fields=["maintenance_mode"])

        SubAction.objects.create(
            action=Action.objects.create(
                prototype=self.host.cluster.prototype,
                name=settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
                host_action=True,
                type=ActionType.JOB,
                state_available="any",
            ),
            script_type="ansible",
            script="something.yaml",
        )

        with RunTaskMock() as run_task:
            response: Response = self.client.post(
                path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
                data={"maintenance_mode": "OFF"},
            )

        self.host.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "CHANGING")
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.CHANGING)

        self.assertIsNotNone(run_task.target_task)
        self.assertEqual(run_task.target_task.task_object, self.host)
        self.assertEqual(run_task.target_task.owner_id, self.host.cluster.pk)
        self.assertEqual(run_task.target_task.owner_type, ADCMCoreType.CLUSTER.value)

        run_task.runner.run(run_task.target_task.pk)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        self.host.refresh_from_db()
        # since MM wasn't changed with plugin, rollback will be preformed
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.ON.value)

    def test_change_mm_off_to_off_with_action_fail(self):
        self.host.maintenance_mode = MaintenanceMode.OFF
        self.host.save(update_fields=["maintenance_mode"])

        with RunTaskMock() as run_task:
            response: Response = self.client.post(
                path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
                data={"maintenance_mode": "OFF"},
            )

        self.host.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.OFF)
        self.assertIsNone(run_task.target_task)

    def test_change_mm_changing_now_fail(self):
        self.host.maintenance_mode = MaintenanceMode.CHANGING
        self.host.save(update_fields=["maintenance_mode"])

        response: Response = self.client.post(
            path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": "ON"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        response: Response = self.client.post(
            path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": "OFF"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_cluster_clear_issue_success(self):
        provider_bundle = self.upload_and_load_bundle(
            path=Path(
                self.base_dir,
                "python/api/tests/files/bundle_test_provider_concern.tar",
            ),
        )

        cluster_bundle = self.upload_and_load_bundle(
            path=Path(
                self.base_dir,
                "python/api/tests/files/bundle_test_cluster_with_mm.tar",
            ),
        )

        provider_prototype = Prototype.objects.get(bundle=provider_bundle, type="provider")
        provider_response: Response = self.client.post(
            path=reverse(viewname="v1:provider"),
            data={"name": "test_provider", "prototype_id": provider_prototype.pk},
        )
        provider = Provider.objects.get(pk=provider_response.data["id"])

        host_response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"provider_id": provider.pk}),
            data={"fqdn": "test-host"},
        )
        host = Host.objects.get(pk=host_response.data["id"])

        self.assertTrue(host.concerns.exists())

        cluster_prototype = Prototype.objects.get(bundle_id=cluster_bundle.pk, type="cluster")
        cluster_response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={"name": "test-cluster", "prototype_id": cluster_prototype.pk},
        )
        cluster = Cluster.objects.get(pk=cluster_response.data["id"])

        service_prototype = Prototype.objects.get(name="test_service", type="service")
        service_response: Response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": cluster.pk}),
            data={"prototype_id": service_prototype.pk},
        )
        service = Service.objects.get(pk=service_response.data["id"])

        component = Component.objects.get(service=service, prototype__name="first_component")

        self.assertFalse(cluster.concerns.exists())

        self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": cluster.pk}),
            data={"host_id": host.pk},
        )

        self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": cluster.pk}),
            data={"hc": [{"service_id": service.pk, "component_id": component.pk, "host_id": host.pk}]},
            content_type=APPLICATION_JSON,
        )

        self.assertTrue(cluster.concerns.exists())

        self.client.post(
            path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": host.pk}),
            data={"maintenance_mode": "ON"},
        )

        # ADCM-5822 mm does not affect concerns
        self.assertTrue(cluster.concerns.exists())

    def test_mm_constraint_by_no_cluster_fail(self):
        self.host.cluster = None
        self.host.save(update_fields=["cluster"])

        response: Response = self.client.post(
            path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": "ON"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_mm_constraint_by_cluster_without_mm_fail(self):
        self.cluster_prototype.allow_maintenance_mode = False
        self.cluster_prototype.save(update_fields=["allow_maintenance_mode"])

        response: Response = self.client.post(
            path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": self.host.pk}),
            data={"maintenance_mode": "ON"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_change_maintenance_mode_on_with_action_via_bundle_success(self):
        bundle = self.upload_and_load_bundle(
            path=Path(
                self.base_dir,
                "python/api/tests/files/cluster_using_plugin.tar",
            ),
        )

        cluster_prototype = Prototype.objects.get(bundle_id=bundle.pk, type="cluster")
        cluster_response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={"name": "test-cluster", "prototype_id": cluster_prototype.pk},
        )
        cluster = Cluster.objects.get(pk=cluster_response.data["id"])

        self.client.post(
            path=reverse(viewname="v1:provider"),
            data={"name": "test_provider", "prototype_id": self.provider_prototype.pk},
        )
        host_response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"provider_id": self.host_provider.pk}),
            data={"fqdn": "test-host"},
        )
        host = Host.objects.get(pk=host_response.data["id"])

        self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": cluster.pk}),
            data={"host_id": host.pk},
        )

        with RunTaskMock() as run_task:
            response: Response = self.client.post(
                path=reverse(viewname="v1:host-maintenance-mode", kwargs={"host_id": host.pk}),
                data={"maintenance_mode": "ON"},
            )

        host.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "CHANGING")
        self.assertEqual(host.maintenance_mode, MaintenanceMode.CHANGING)

        self.assertIsNotNone(run_task.target_task)
        self.assertEqual(run_task.target_task.task_object, host)
        self.assertEqual(run_task.target_task.owner_id, host.cluster.pk)
        self.assertEqual(run_task.target_task.owner_type, ADCMCoreType.CLUSTER.value)

        run_task.runner.run(run_task.target_task.pk)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        host.refresh_from_db()
        # since MM wasn't changed with plugin, rollback will be preformed
        self.assertEqual(host.maintenance_mode, MaintenanceMode.OFF.value)
