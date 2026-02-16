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

from cm.models import Component, Host, MaintenanceMode, Service, TaskLog
from cm.tests.mocks.task_runner import ExecutionTargetFactoryDummyMock, FailedJobInfo
from core.types import TaskID
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
        self.task_runner.reset()

        self.executor_with_failed_first_job = ExecutionTargetFactoryDummyMock(
            failed_job=FailedJobInfo(position=0, return_code=1)
        )

        bundle_mm_plugins_mm_actions = self.add_bundle(
            source_dir=self.test_bundles_dir / "maintenance_mode" / "mm_plugins_mm_actions"
        )
        self.cluster = self.add_cluster(bundle=bundle_mm_plugins_mm_actions, name="cluster_mm_plugins_mm_actions")
        self.service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster).get()
        self.component = self.service.components.get(prototype__name="component_1")

        provider_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "provider")
        provider = self.add_provider(bundle=provider_bundle, name="provider", description="provider")
        self.host = self.add_host(provider=provider, fqdn="host")

    def do_change_mm_request(self, obj: Host | Service | Component) -> Response:
        match obj.maintenance_mode:
            case MaintenanceMode.ON:
                data = {"maintenanceMode": MaintenanceMode.OFF.value}
            case MaintenanceMode.OFF:
                data = {"maintenanceMode": MaintenanceMode.ON.value}
            case _:
                raise ValueError(f"Unexpected mm status: {obj.maintenance_mode}")

        object_endpoint = self.client.v2[(obj.cluster, "hosts", obj) if isinstance(obj, Host) else obj]

        return (object_endpoint / "maintenance-mode").post(data=data)

    def expect_task_launched_with_name(self, name: str) -> TaskID:
        task_id = self.task_runner.expect_task_launched().id
        actual_name = TaskLog.objects.values_list("name", flat=True).get()
        self.assertEqual(actual_name, name)
        return task_id

    def test_no_task_run_without_hc_service(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)

        response = self.do_change_mm_request(obj=self.service)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.service.refresh_from_db()
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.ON)
        self.task_runner.expect_task_not_launched()

    def test_task_run_if_hc_exists_service(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.set_hostcomponent(cluster=self.cluster, entries=[(self.host, self.component)])

        response = self.do_change_mm_request(obj=self.service)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.service.refresh_from_db()
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.CHANGING)
        self.expect_task_launched_with_name("adcm_turn_on_maintenance_mode")

    def test_no_task_run_without_hc_component(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)

        response = self.do_change_mm_request(obj=self.component)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.component.refresh_from_db()
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.ON)
        self.task_runner.expect_task_not_launched()

    def test_task_run_if_hc_exists_component(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.set_hostcomponent(cluster=self.cluster, entries=[(self.host, self.component)])

        response = self.do_change_mm_request(obj=self.component)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.component.refresh_from_db()
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.CHANGING)
        self.expect_task_launched_with_name("adcm_turn_on_maintenance_mode")

    def test_task_run_if_obj_is_host_without_hc(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)

        response = self.do_change_mm_request(obj=self.host)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.CHANGING)
        self.expect_task_launched_with_name("adcm_host_turn_on_maintenance_mode")

    def test_task_run_if_obj_is_host_hc_exists(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.set_hostcomponent(cluster=self.cluster, entries=[(self.host, self.component)])

        response = self.do_change_mm_request(obj=self.host)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.CHANGING)
        self.expect_task_launched_with_name("adcm_host_turn_on_maintenance_mode")

    def test_mm_not_changed_on_fail_service(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.set_hostcomponent(cluster=self.cluster, entries=[(self.host, self.component)])
        initial_object_mm = self.service.maintenance_mode

        response = self.do_change_mm_request(obj=self.service)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.service.refresh_from_db()
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.CHANGING)
        task_id = self.expect_task_launched_with_name("adcm_turn_on_maintenance_mode")

        self.task_runner.run_task(task_id=task_id, execution_target_factory=self.executor_with_failed_first_job)

        self.service.refresh_from_db()
        self.assertEqual(self.service.maintenance_mode, initial_object_mm)

    def test_mm_not_changed_on_fail_component(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.set_hostcomponent(cluster=self.cluster, entries=[(self.host, self.component)])
        initial_object_mm = self.component.maintenance_mode

        response = self.do_change_mm_request(obj=self.component)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.component.refresh_from_db()
        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.CHANGING)
        task_id = self.expect_task_launched_with_name("adcm_turn_on_maintenance_mode")

        self.task_runner.run_task(task_id=task_id, execution_target_factory=self.executor_with_failed_first_job)

        self.component.refresh_from_db()
        self.assertEqual(self.component.maintenance_mode, initial_object_mm)

    def test_mm_not_changed_on_fail_host(self):
        self.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.set_hostcomponent(cluster=self.cluster, entries=[(self.host, self.component)])
        initial_object_mm = self.host.maintenance_mode

        response = self.do_change_mm_request(obj=self.host)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.CHANGING)
        task_id = self.expect_task_launched_with_name("adcm_host_turn_on_maintenance_mode")

        self.task_runner.run_task(task_id=task_id, execution_target_factory=self.executor_with_failed_first_job)

        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, initial_object_mm)
