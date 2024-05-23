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

from cm.models import ClusterObject, Host, MaintenanceMode, ServiceComponent
from cm.tests.mocks.task_runner import ExecutionTargetFactoryDummyMock, FailedJobInfo, RunTaskMock
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from api_v2.tests.base import BaseAPITestCase


class TestMMActions(BaseAPITestCase):
    """
    Tests for reserved mm-action names
    No actual ansible playbook runs, thus checking for `changing` mm status
    """

    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        bundle_mm_plugins_mm_actions = self.add_bundle(
            source_dir=self.test_bundles_dir / "maintenance_mode" / "mm_plugins_mm_actions"
        )
        self.cluster = self.add_cluster(bundle=bundle_mm_plugins_mm_actions, name="cluster_mm_plugins_mm_actions")
        self.service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster).get()
        self.component = self.service.servicecomponent_set.get(prototype__name="component_1")

        provider_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "provider")
        provider = self.add_provider(bundle=provider_bundle, name="provider", description="provider")
        self.host = self.add_host(bundle=provider_bundle, provider=provider, fqdn="host")

    def _do_change_mm_request(
        self, obj: Host | ClusterObject | ServiceComponent, failed_job: FailedJobInfo | None = None
    ) -> tuple[Response, RunTaskMock]:
        match obj.maintenance_mode:
            case MaintenanceMode.ON:
                data = {"maintenanceMode": MaintenanceMode.OFF.value}
            case MaintenanceMode.OFF:
                data = {"maintenanceMode": MaintenanceMode.ON.value}
            case _:
                raise ValueError(f"Unexpected mm status: {obj.maintenance_mode}")

        object_endpoint = self.client.v2[(obj.cluster, "hosts", obj) if isinstance(obj, Host) else obj]

        run_task_mock_kwargs = {}
        if failed_job:
            run_task_mock_kwargs = {"execution_target_factory": ExecutionTargetFactoryDummyMock(failed_job=failed_job)}

        with RunTaskMock(**run_task_mock_kwargs) as run_task_mock:
            response = (object_endpoint / "maintenance-mode").post(data=data)

        return response, run_task_mock

    def test_no_task_run_without_hc_service(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)

        response, run_task_mock = self._do_change_mm_request(obj=self.service)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.service.refresh_from_db()
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.ON)
        self.assertIsNone(run_task_mock.target_task)
        self.assertIsNone(run_task_mock.runner)

    def test_task_run_if_hc_exists_service(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.add_hostcomponent_map(
            cluster=self.cluster,
            hc_map=[{"host_id": self.host.pk, "service_id": self.service.pk, "component_id": self.component.pk}],
        )

        response, run_task_mock = self._do_change_mm_request(obj=self.service)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.service.refresh_from_db()
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.CHANGING)
        self.assertIsNotNone(run_task_mock.target_task)
        self.assertEqual(run_task_mock.target_task.action.name, "adcm_turn_on_maintenance_mode")
        self.assertIsNotNone(run_task_mock.runner)

    def test_no_task_run_without_hc_component(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)

        response, run_task_mock = self._do_change_mm_request(obj=self.component)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.component.refresh_from_db()
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.ON)
        self.assertIsNone(run_task_mock.target_task)
        self.assertIsNone(run_task_mock.runner)

    def test_task_run_if_hc_exists_component(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.add_hostcomponent_map(
            cluster=self.cluster,
            hc_map=[{"host_id": self.host.pk, "service_id": self.service.pk, "component_id": self.component.pk}],
        )

        response, run_task_mock = self._do_change_mm_request(obj=self.component)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.component.refresh_from_db()
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.CHANGING)
        self.assertIsNotNone(run_task_mock.target_task)
        self.assertEqual(run_task_mock.target_task.action.name, "adcm_turn_on_maintenance_mode")
        self.assertIsNotNone(run_task_mock.runner)

    def test_task_run_if_obj_is_host_without_hc(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)

        response, run_task_mock = self._do_change_mm_request(obj=self.host)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.CHANGING)
        self.assertIsNotNone(run_task_mock.target_task)
        self.assertEqual(run_task_mock.target_task.action.name, "adcm_host_turn_on_maintenance_mode")
        self.assertIsNotNone(run_task_mock.runner)

    def test_task_run_if_obj_is_host_hc_exists(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.add_hostcomponent_map(
            cluster=self.cluster,
            hc_map=[{"host_id": self.host.pk, "service_id": self.service.pk, "component_id": self.component.pk}],
        )

        response, run_task_mock = self._do_change_mm_request(obj=self.host)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.CHANGING)
        self.assertIsNotNone(run_task_mock.target_task)
        self.assertEqual(run_task_mock.target_task.action.name, "adcm_host_turn_on_maintenance_mode")
        self.assertIsNotNone(run_task_mock.runner)

    def test_mm_not_changed_on_fail_service(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.add_hostcomponent_map(
            cluster=self.cluster,
            hc_map=[{"host_id": self.host.pk, "service_id": self.service.pk, "component_id": self.component.pk}],
        )
        initial_object_mm = self.service.maintenance_mode

        response, run_task_mock = self._do_change_mm_request(
            obj=self.service, failed_job=FailedJobInfo(position=0, return_code=1)
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.service.refresh_from_db()
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.CHANGING)
        self.assertIsNotNone(run_task_mock.target_task)
        self.assertEqual(run_task_mock.target_task.action.name, "adcm_turn_on_maintenance_mode")
        self.assertIsNotNone(run_task_mock.runner)

        run_task_mock.runner.run(task_id=run_task_mock.target_task.pk)
        self.service.refresh_from_db()
        self.assertEqual(self.service.maintenance_mode, initial_object_mm)

    def test_mm_not_changed_on_fail_component(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.add_hostcomponent_map(
            cluster=self.cluster,
            hc_map=[{"host_id": self.host.pk, "service_id": self.service.pk, "component_id": self.component.pk}],
        )
        initial_object_mm = self.component.maintenance_mode

        response, run_task_mock = self._do_change_mm_request(
            obj=self.component, failed_job=FailedJobInfo(position=0, return_code=1)
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.component.refresh_from_db()
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.CHANGING)
        self.assertIsNotNone(run_task_mock.target_task)
        self.assertEqual(run_task_mock.target_task.action.name, "adcm_turn_on_maintenance_mode")
        self.assertIsNotNone(run_task_mock.runner)

        run_task_mock.runner.run(task_id=run_task_mock.target_task.pk)
        self.component.refresh_from_db()
        self.assertEqual(self.component.maintenance_mode, initial_object_mm)

    def test_mm_not_changed_on_fail_host(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.add_hostcomponent_map(
            cluster=self.cluster,
            hc_map=[{"host_id": self.host.pk, "service_id": self.service.pk, "component_id": self.component.pk}],
        )
        initial_object_mm = self.host.maintenance_mode

        response, run_task_mock = self._do_change_mm_request(
            obj=self.host, failed_job=FailedJobInfo(position=0, return_code=1)
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.CHANGING)
        self.assertIsNotNone(run_task_mock.target_task)
        self.assertEqual(run_task_mock.target_task.action.name, "adcm_host_turn_on_maintenance_mode")
        self.assertIsNotNone(run_task_mock.runner)

        run_task_mock.runner.run(task_id=run_task_mock.target_task.pk)
        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, initial_object_mm)
