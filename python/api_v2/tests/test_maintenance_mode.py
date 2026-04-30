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

from cm.converters import orm_object_to_action_target_descriptor
from cm.models import Action, Component, Host, MaintenanceMode, Service, TaskLog
from cm.tests.mocks.task_runner import FailedJobInfo
from cm.transition.action import RetrieveStartImpossibleReason
from core.types import TaskID
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_409_CONFLICT
from tests.dependencies import TaskRunnerOverride
from tests.suites import ADCMDjangoAPISuite


class MMUtilsMixin:
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


class TestMMActions(ADCMDjangoAPISuite, MMUtilsMixin):
    """
    Tests for reserved mm-action names
    No actual ansible playbook runs, thus checking for `changing` mm status
    """

    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cls.executor_with_failed_first_job_overrides = (
            TaskRunnerOverride(failed_job=FailedJobInfo(position=0, return_code=1)),
        )

        bundle_mm_plugins_mm_actions = cls.uc.upload_bundle(
            src=cls.test_bundles_dir / "maintenance_mode" / "mm_plugins_mm_actions"
        )
        cls.cluster = cls.uc.add_cluster(bundle=bundle_mm_plugins_mm_actions, name="cluster_mm_plugins_mm_actions")
        cls.service, *_ = cls.uc.add_services_to_cluster(["service_1"], cluster=cls.cluster)
        cls.component = cls.service.components.get(prototype__name="component_1")

        provider_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider")
        provider = cls.uc.add_provider(bundle=provider_bundle, name="provider", description="provider")
        cls.host = cls.uc.add_host(provider=provider, fqdn="host")

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

    def test_start_impossible_reason_does_not_affects_mm_actions(self):
        mm_action_name = "adcm_turn_on_maintenance_mode"
        service, *_ = self.uc.add_services_to_cluster(["service_2"], cluster=self.cluster)
        component_1 = service.components.get(prototype__name="component_1")
        component_2 = service.components.get(prototype__name="component_2")

        self.uc.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.uc.set_hostcomponent(cluster=self.cluster, entries=[(self.host, component_1), (self.host, self.component)])

        # put one component in MM, retrieve service's SIR
        mm_action = Action.objects.get(name=mm_action_name, prototype=service.prototype)
        retrieve_sir = self.container.get(RetrieveStartImpossibleReason)
        component_2._maintenance_mode = "on"
        component_2.save(update_fields=["_maintenance_mode"])
        service_sir = retrieve_sir.for_action_target(
            target=orm_object_to_action_target_descriptor(service),
            allowed_in_mm={mm_action.id: mm_action.allow_in_maintenance_mode},
        )[mm_action.pk]
        self.assertEqual(service_sir, 'The Action is not available. One or more components in "Maintenance mode"')

        response = self.do_change_mm_request(obj=service)

        self.assertEqual(response.status_code, HTTP_200_OK)

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

        self.task_runner.run_task(task_id=task_id, overrides=self.executor_with_failed_first_job_overrides)

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

        self.task_runner.run_task(task_id=task_id, overrides=self.executor_with_failed_first_job_overrides)

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

        self.task_runner.run_task(task_id=task_id, overrides=self.executor_with_failed_first_job_overrides)

        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, initial_object_mm)

    def test_adcm_8005_sir_does_not_affects_mm_action_run(self):
        endpoint = self.client.v2[self.cluster, "hosts", self.host, "maintenance-mode"]
        self.uc.add_host_to_cluster(cluster=self.cluster, host=self.host)
        self.uc.set_hostcomponent(cluster=self.cluster, entries=[(self.host, self.component)])

        # set mm to 'on'
        self.host.maintenance_mode = "on"
        self.host.save(update_fields=["maintenance_mode"])

        expected_sir = 'The Action is not available. One or more hosts in "Maintenance mode"'
        sir_retriever = self.uc.container.get(RetrieveStartImpossibleReason)
        mm_action = Action.objects.get(
            name="adcm_host_turn_off_maintenance_mode", host_action=True, prototype=self.cluster.prototype
        )
        sir = sir_retriever.for_action_target(
            target=orm_object_to_action_target_descriptor(self.host),
            allowed_in_mm={mm_action.pk: mm_action.allow_in_maintenance_mode},
        )[mm_action.pk]
        self.assertEqual(sir, expected_sir)

        # turn MM off via action
        response = endpoint.post(data={"maintenanceMode": "off"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.maintenance_mode, MaintenanceMode.CHANGING)
        task_id = self.task_runner.expect_task_launched().id

        # ensure correct task was launched
        task = TaskLog.objects.get(pk=task_id)
        self.assertEqual(task.action_id, mm_action.id)


class TestMaintenanceMode(ADCMDjangoAPISuite, MMUtilsMixin):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cluster_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_one")
        cls.cluster = cls.uc.add_cluster(bundle=cluster_bundle, name="test-cluster")
        cls.service, *_ = cls.uc.add_services_to_cluster(["service_1"], cluster=cls.cluster)
        cls.component_1 = cls.service.components.get(prototype__name="component_1")
        cls.component_2 = cls.service.components.get(prototype__name="component_2")
        cls.component_3 = cls.service.components.get(prototype__name="component_3")

        provider_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider")
        provider = cls.uc.add_provider(bundle=provider_bundle, name="provider", description="provider")
        cls.host_1 = cls.uc.add_host(provider=provider, fqdn="host-1", cluster=cls.cluster)
        cls.host_2 = cls.uc.add_host(provider=provider, fqdn="host-2", cluster=cls.cluster)
        cls.host_3 = cls.uc.add_host(provider=provider, fqdn="host-3", cluster=cls.cluster)

        cls.uc.set_hostcomponent(
            cluster=cls.cluster,
            entries=((cls.host_1, cls.component_1), (cls.host_2, cls.component_2), (cls.host_3, cls.component_3)),
        )

    def test_turn_off_mm_service_in_implicit_mm_from_hosts(self):
        # turn ON mm on all hosts
        for host in (self.host_1, self.host_2, self.host_3):
            response = self.do_change_mm_request(obj=host)
            self.assertEqual(response.status_code, HTTP_200_OK)

            host.refresh_from_db()
            self.assertEqual(host.maintenance_mode, MaintenanceMode.ON)

        expected_response = {
            "code": "MAINTENANCE_MODE",
            "level": "error",
            "desc": "The service is in maintenance mode because the hosts where it is installed are in maintenance "
            "mode. To turn it off, disable maintenance mode on related hosts.",
        }

        response = self.do_change_mm_request(obj=self.service)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)

    def test_turn_off_mm_service_in_implicit_mm_from_components(self):
        # turn ON mm on all components
        for component in (self.component_1, self.component_2, self.component_3):
            response = self.do_change_mm_request(obj=component)
            self.assertEqual(response.status_code, HTTP_200_OK)

            component.refresh_from_db()
            self.assertEqual(component.maintenance_mode, MaintenanceMode.ON)

        expected_response = {
            "code": "MAINTENANCE_MODE",
            "level": "error",
            "desc": "The service is in maintenance mode because all it's components are in maintenance mode. "
            "To turn it off, disable maintenance mode on related components.",
        }

        response = self.do_change_mm_request(obj=self.service)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)

    def test_turn_off_mm_service_not_in_mm(self):
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.OFF)

        expected_response = {
            "code": "MAINTENANCE_MODE",
            "level": "error",
            "desc": "Maintenance mode already off.",
        }

        response = (self.client.v2[self.service] / "maintenance-mode").post(
            data={"maintenanceMode": MaintenanceMode.OFF.value}
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)

    def test_turn_off_mm_component_in_implicit_mm_from_service(self):
        response = self.do_change_mm_request(obj=self.service)
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.service.refresh_from_db()
        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.ON)

        expected_response = {
            "code": "MAINTENANCE_MODE",
            "level": "error",
            "desc": "The component is in maintenance mode because it's service is in maintenance mode. "
            "To turn it off, disable maintenance mode on related service.",
        }

        response = self.do_change_mm_request(obj=self.component_1)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)

    def test_turn_off_mm_component_in_implicit_mm_from_hosts(self):
        response = self.do_change_mm_request(obj=self.host_1)
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.host_1.refresh_from_db()
        self.assertEqual(self.host_1.maintenance_mode, MaintenanceMode.ON)

        expected_response = {
            "code": "MAINTENANCE_MODE",
            "level": "error",
            "desc": "The component is in maintenance mode because the hosts where it is installed are in maintenance "
            "mode. To turn it off, disable maintenance mode on related hosts.",
        }

        response = self.do_change_mm_request(obj=self.component_1)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)

    def test_turn_off_mm_component_not_in_mm(self):
        self.assertEqual(self.component_1.maintenance_mode, MaintenanceMode.OFF)

        expected_response = {
            "code": "MAINTENANCE_MODE",
            "level": "error",
            "desc": "Maintenance mode already off.",
        }

        response = (self.client.v2[self.component_1] / "maintenance-mode").post(
            data={"maintenanceMode": MaintenanceMode.OFF.value}
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)

    def test_turn_off_mm_host_not_in_mm(self):
        self.assertEqual(self.host_1.maintenance_mode, MaintenanceMode.OFF)

        expected_response = {
            "code": "MAINTENANCE_MODE",
            "level": "error",
            "desc": "Maintenance mode already off.",
        }

        # host endpoint
        response = (self.client.v2[self.host_1] / "maintenance-mode").post(
            data={"maintenanceMode": MaintenanceMode.OFF.value}
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)

        # cluster-host endpoint
        response = (self.client.v2[(self.host_1.cluster, "hosts", self.host_1)] / "maintenance-mode").post(
            data={"maintenanceMode": MaintenanceMode.OFF.value}
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)
