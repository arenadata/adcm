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

from typing import NamedTuple
from unittest.mock import patch

from cm.models import (
    Action,
    ActionHostGroup,
    ADCMEntityStatus,
    Cluster,
    ClusterBind,
    Component,
    ConcernType,
    ConfigHostGroup,
    HostComponent,
    JobLog,
    JobStatus,
    MaintenanceMode,
    ObjectType,
    Prototype,
    Service,
    TaskLog,
)
from cm.services.job.action import ActionRunPayload, run_action
from cm.services.status.client import FullStatusMap
from cm.tests.mocks.task_runner import RunTaskMock
from django.contrib.contenttypes.models import ContentType
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class FakePopenResponse(NamedTuple):
    pid: int


class TestServiceAPI(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.service_2 = self.add_services_to_cluster(service_names=["service_2"], cluster=self.cluster_1).get()
        self.action = Action.objects.filter(prototype=self.service_2.prototype).first()

    def test_list_success(self):
        response = self.client.v2[self.cluster_1, "services"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_adcm_4544_service_ordering_success(self):
        service_3 = self.add_services_to_cluster(service_names=["service_3_manual_add"], cluster=self.cluster_1).get()
        self.service_2.state, service_3.state = "non_created", "installed"

        for service in (self.service_1, self.service_2, service_3):
            service.save()

        response = self.client.v2[self.cluster_1, "services"].get(query={"ordering": "displayName"})
        self.assertListEqual(
            [service["displayName"] for service in response.json()["results"]],
            list(Service.objects.order_by("prototype__display_name").values_list("prototype__display_name", flat=True)),
        )

        response = self.client.v2[self.cluster_1, "services"].get(query={"ordering": "-displayName"})
        self.assertListEqual(
            [service["displayName"] for service in response.json()["results"]],
            list(
                Service.objects.order_by("-prototype__display_name").values_list("prototype__display_name", flat=True)
            ),
        )

    def test_retrieve_success(self):
        response = self.client.v2[self.service_2].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.service_2.pk)
        self.assertEqual(response.json()["description"], self.service_2.description)

    def test_delete_success(self):
        response = self.client.v2[self.service_2].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Service.objects.filter(pk=self.service_2.pk).exists())

    def test_adcm_6083_delete_service_with_stale_task_from_deleted_bundle(self):
        # create stale task with `created` status
        non_existent_cluster_id = self.get_non_existent_pk(model=Cluster)
        cluster_ct = ContentType.objects.get_for_model(Cluster)
        TaskLog.objects.create(
            object_id=non_existent_cluster_id,
            object_type=cluster_ct,
            owner_id=non_existent_cluster_id,
            owner_type=cluster_ct.model,
            action=None,
            status=JobStatus.CREATED,
        )

        response = self.client.v2[self.service_2].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Service.objects.filter(pk=self.service_2.pk).exists())

    def test_delete_wrong_state_failed(self):
        self.service_2.state = "non_created"
        self.service_2.save(update_fields=["state"])

        response = self.client.v2[self.service_2].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_DELETE_ERROR",
                "desc": "Service can't be deleted if it has not CREATED state",
                "level": "error",
            },
        )
        self.assertTrue(Service.objects.filter(pk=self.service_2.pk).exists())

    def test_delete_mapping_exists_fail(self):
        host = self.add_host(provider=self.provider, fqdn="test-host", cluster=self.cluster_1)
        component = self.service_1.components.first()
        self.set_hostcomponent(cluster=self.cluster_1, entries=((host, component),))

        response = self.client.v2[self.service_1].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_CONFLICT",
                "desc": f'Service "{self.service_1.display_name}" has component(s) on host(s)',
                "level": "error",
            },
        )
        self.assertTrue(Service.objects.filter(pk=self.service_1.pk).exists())

    def test_delete_during_cluster_upgrading_fail(self):
        self.cluster_1.state = "upgrading"
        self.cluster_1.before_upgrade = {"services": (self.service_1.prototype.name,)}
        self.cluster_1.save(update_fields=["state", "before_upgrade"])

        response = self.client.v2[self.service_1].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "SERVICE_CONFLICT", "desc": "Can't remove service when upgrading cluster", "level": "error"},
        )
        self.assertTrue(Service.objects.filter(pk=self.service_1.pk).exists())

    def test_delete_with_export_exists_fail(self):
        service_2 = self.add_services_to_cluster(service_names=["service"], cluster=self.cluster_2).get()
        ClusterBind.objects.create(
            cluster_id=service_2.cluster.pk,
            service_id=service_2.pk,
            source_cluster_id=self.service_1.cluster.pk,
            source_service_id=self.service_1.pk,
        )

        response = self.client.v2[self.service_1].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_CONFLICT",
                "desc": f'Service "{self.service_1.prototype.display_name}" has exports(s)',
                "level": "error",
            },
        )
        self.assertTrue(Service.objects.filter(pk=self.service_1.pk).exists())

    def test_delete_required_service_fail(self):
        prototype = self.service_1.prototype
        prototype.required = True
        prototype.save(update_fields=["required"])

        response = self.client.v2[self.service_1].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_CONFLICT",
                "desc": f'Service "{self.service_1.prototype.display_name}" is required',
                "level": "error",
            },
        )
        self.assertTrue(Service.objects.filter(pk=self.service_1.pk).exists())

    def test_delete_required_by_other_service_fail(self):
        bundle_dir = self.test_bundles_dir / "cluster_with_service_requirements"
        bundle = self.add_bundle(source_dir=bundle_dir)
        cluster = self.add_cluster(bundle=bundle, name="service_requirements_cluster")
        service = self.add_services_to_cluster(service_names=["service_1", "some_other_service"], cluster=cluster).get(
            prototype__name="some_other_service"
        )
        service_1 = cluster.services.get(prototype__name="service_1")

        response = self.client.v2[service].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_CONFLICT",
                "desc": f'Service "{service_1.display_name}" requires this service or its component',
                "level": "error",
            },
        )
        self.assertTrue(Service.objects.filter(pk=service.pk).exists())

    def test_delete_required_by_other_component_only_service_fail(self):
        bundle_dir = self.test_bundles_dir / "cluster_with_service_requirements"
        bundle = self.add_bundle(source_dir=bundle_dir)
        cluster = self.add_cluster(bundle=bundle, name="service_requirements_cluster")
        service = self.add_services_to_cluster(
            service_names=["some_other_service", "third_service"], cluster=cluster
        ).get(prototype__name="some_other_service")
        third_service = cluster.services.get(prototype__name="third_service")
        component = third_service.components.get(prototype__name="component_from_third_service")

        response = self.client.v2[service].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_CONFLICT",
                "desc": f'Component "{component.prototype.name}" of service "{third_service.prototype.display_name} '
                f"requires this service or its component",
                "level": "error",
            },
        )
        self.assertTrue(Service.objects.filter(pk=service.pk).exists())

    def test_delete_required_by_other_component_full_requires_fail(self):
        bundle_dir = self.test_bundles_dir / "cluster_with_service_requirements"
        bundle = self.add_bundle(source_dir=bundle_dir)
        cluster = self.add_cluster(bundle=bundle, name="service_requirements_cluster")
        service = self.add_services_to_cluster(
            service_names=["some_other_service", "fourth_service"], cluster=cluster
        ).get(prototype__name="some_other_service")
        fourth_service = cluster.services.get(prototype__name="fourth_service")
        component = fourth_service.components.get(prototype__name="component_from_fourth_service")

        response = self.client.v2[service].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_CONFLICT",
                "desc": f'Component "{component.prototype.name}" of service "{fourth_service.prototype.display_name} '
                f"requires this service or its component",
                "level": "error",
            },
        )
        self.assertTrue(Service.objects.filter(pk=service.pk).exists())

    def test_adcm_6146_delete_generic_relations_on_service_deletion(self):
        response = self.client.v2[self.service_1, "config-groups"].post(data={"name": "Service CHG"})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        service_chg_id = response.json()["id"]
        self.assertTrue(ConfigHostGroup.objects.filter(pk=service_chg_id).exists())

        response = self.client.v2[self.service_1, "action-host-groups"].post(data={"name": "Service AHG"})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        service_ahg_id = response.json()["id"]
        self.assertTrue(ActionHostGroup.objects.filter(pk=service_ahg_id).exists())

        component = self.service_1.components.get(prototype__name="component_1")

        response = self.client.v2[component, "config-groups"].post(data={"name": "Component CHG"})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        component_chg_id = response.json()["id"]
        self.assertTrue(ConfigHostGroup.objects.filter(pk=component_chg_id).exists())

        response = self.client.v2[component, "action-host-groups"].post(data={"name": "Component AHG"})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        component_ahg_id = response.json()["id"]
        self.assertTrue(ActionHostGroup.objects.filter(pk=component_ahg_id).exists())

        response = self.client.v2[self.service_1].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Service.objects.filter(pk=self.service_1.pk).exists())
        self.assertFalse(Component.objects.filter(pk=component.pk).exists())

        self.assertFalse(ConfigHostGroup.objects.filter(pk=service_chg_id).exists())
        self.assertFalse(ActionHostGroup.objects.filter(pk=service_ahg_id).exists())

        self.assertFalse(ConfigHostGroup.objects.filter(pk=component_chg_id).exists())
        self.assertFalse(ActionHostGroup.objects.filter(pk=component_ahg_id).exists())

    def test_create_success(self):
        initial_service_count = Service.objects.count()
        manual_add_service_proto = Prototype.objects.get(type=ObjectType.SERVICE, name="service_3_manual_add")

        response = self.client.v2[self.cluster_1, "services"].post(data=[{"prototypeId": manual_add_service_proto.pk}])

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["prototype"]["id"], manual_add_service_proto.pk)

        self.assertEqual(Service.objects.count(), initial_service_count + 1)

    def test_add_one_success(self):
        initial_service_count = Service.objects.count()
        manual_add_service_proto = Prototype.objects.get(type=ObjectType.SERVICE, name="service_3_manual_add")

        response = self.client.v2[self.cluster_1, "services"].post(data={"prototypeId": manual_add_service_proto.pk})

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["prototype"]["id"], manual_add_service_proto.pk)

        self.assertEqual(Service.objects.count(), initial_service_count + 1)

    def test_create_wrong_data_fail(self):
        initial_service_count = Service.objects.count()
        manual_add_service_proto = Prototype.objects.get(type=ObjectType.SERVICE, name="service_3_manual_add")

        response = self.client.v2[self.cluster_1, "services"].post(data={"somekey": manual_add_service_proto.pk})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(Service.objects.count(), initial_service_count)

    def test_filtering_success(self):
        filters = {
            "name": (self.service_1.name, self.service_1.name[1:-2].upper(), "wrong"),
            "display_name": (self.service_1.display_name, self.service_1.display_name[1:-2].upper(), "wrong"),
        }
        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            partial_items_found = 1 if filter_name in ("maintenance_mode", "id") else 2
            with self.subTest(filter_name=filter_name):
                response = self.client.v2[self.cluster_1, "services"].get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)

                response = self.client.v2[self.cluster_1, "services"].get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

                if partial_value:
                    response = self.client.v2[self.cluster_1, "services"].get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], partial_items_found)

    def test_filter_by_status_success(self):
        status_map = FullStatusMap(
            clusters={
                str(self.cluster_1.pk): {
                    "status": 16,
                    "hosts": {},
                    "services": {
                        str(self.service_1.pk): {"status": 16, "components": {}, "details": []},
                        str(self.service_2.pk): {"status": 0, "components": {}, "details": []},
                    },
                }
            }
        )

        with patch("api_v2.filters.retrieve_status_map", return_value=status_map):
            response = self.client.v2[self.cluster_1, "services"].get(query={"status": ADCMEntityStatus.UP})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["id"], self.service_2.pk)

    def test_limit_offset_success(self):
        response = self.client.v2[self.cluster_1, "services"].get(query={"limit": 1, "offset": 1})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_change_mm(self):
        response = self.client.v2[self.service_2, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.ON}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_action_list_success(self):
        response = self.client.v2[self.service_2, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_action_retrieve_success(self):
        response = self.client.v2[self.service_2, "actions", self.action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_action_run_success(self):
        with RunTaskMock() as run_task:
            response = self.client.v2[self.service_2, "actions", self.action, "run"].post(
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], run_task.target_task.id)
        self.assertEqual(run_task.target_task.status, "created")

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")


class TestServiceDeleteAction(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_to_delete, *_ = self.add_services_to_cluster(
            service_names=["service_6_delete_with_action"], cluster=self.cluster_1
        )
        self.service_regular_action: Action = Action.objects.get(
            prototype=self.service_to_delete.prototype, name="regular_action"
        )
        self.cluster_regular_action: Action = Action.objects.get(prototype=self.cluster_1.prototype, name="action")
        HostComponent.objects.create(
            cluster=self.cluster_1,
            service=self.service_to_delete,
            component=Component.objects.get(service=self.service_to_delete, prototype__name="component"),
            host=self.add_host(
                bundle=self.provider_bundle, provider=self.provider, fqdn="doesntmatter", cluster=self.cluster_1
            ),
        )

    def test_delete_service_do_not_abort_cluster_actions_fail(self) -> None:
        self.imitate_task_running(action=self.cluster_regular_action, object_=self.cluster_1)

        self.assertTrue(self.service_to_delete.concerns.filter(type=ConcernType.LOCK).exists())

        with patch("subprocess.Popen", return_value=FakePopenResponse(3)), patch("os.kill", return_type=None):
            response = self.client.v2[self.service_to_delete].delete()

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "LOCK_ERROR")

    def test_delete_service_abort_own_actions_success(self) -> None:
        self.imitate_task_running(action=self.service_regular_action, object_=self.service_to_delete)

        self.assertTrue(self.service_to_delete.concerns.filter(type=ConcernType.LOCK).exists())

        with patch("subprocess.Popen", return_value=FakePopenResponse(3)), patch("os.kill", return_type=None):
            response = self.client.v2[self.service_to_delete].delete()

            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

            service_concerns_qs = self.service_to_delete.concerns.filter(type=ConcernType.LOCK)
            # one for old job, one for delete job
            self.assertEqual(service_concerns_qs.count(), 2)
            self.assertTrue(service_concerns_qs.filter(name="adcm_delete_service").exists())

    @staticmethod
    def imitate_task_running(action: Action, object_: Cluster | Service) -> TaskLog:
        with patch("subprocess.Popen", return_value=FakePopenResponse(4)):
            task = run_action(action=action, obj=object_, payload=ActionRunPayload())

        job = JobLog.objects.filter(task=task).first()
        job.status = "running"
        job.save(update_fields=["status"])

        task.status = "running"
        task.pid = 4
        task.save(update_fields=["status", "pid"])

        return task


class TestServiceMaintenanceMode(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1_cl_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1_s_1_cl1 = Component.objects.filter(
            cluster_id=self.cluster_1.pk, service_id=self.service_1_cl_1.pk
        ).last()
        self.service_cl_2 = self.add_services_to_cluster(service_names=["service"], cluster=self.cluster_2).get()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def test_change_mm_success(self):
        response = self.client.v2[self.service_1_cl_1, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.ON}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_adcm_5277_change_mm_service_service_administrator_success(self):
        with self.grant_permissions(to=self.test_user, on=self.service_1_cl_1, role_name="Service Administrator"):
            response = self.client.v2[self.service_1_cl_1, "maintenance-mode"].post(
                data={"maintenance_mode": MaintenanceMode.ON}
            )
            self.service_1_cl_1.refresh_from_db()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(self.service_1_cl_1.maintenance_mode, MaintenanceMode.ON)

    def test_adcm_5277_change_mm_component_service_administrator_success(self):
        with self.grant_permissions(to=self.test_user, on=self.service_1_cl_1, role_name="Service Administrator"):
            response = self.client.v2[self.component_1_s_1_cl1, "maintenance-mode"].post(
                data={"maintenance_mode": MaintenanceMode.ON}
            )
            self.component_1_s_1_cl1.refresh_from_db()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(self.component_1_s_1_cl1.maintenance_mode, MaintenanceMode.ON)

    def test_change_mm_not_available_fail(self):
        response = self.client.v2[self.service_cl_2, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.ON}
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "MAINTENANCE_MODE_NOT_AVAILABLE",
                "level": "error",
                "desc": "Service does not support maintenance mode",
            },
        )


class TestServicePermissions(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="doesntmatter", cluster=self.cluster_1)
        self.host_with_component = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="doesntmatter_2", cluster=self.cluster_1
        )
        component = Component.objects.filter(cluster_id=self.cluster_1.pk, service_id=self.service.pk).last()
        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_with_component, component)])

    def test_adcm_5278_cluster_hosts_restriction_by_service_administrator_ownership_success(self):
        response_list = self.client.v2[self.cluster_1, "hosts"].get()

        response_detail = self.client.v2[self.cluster_1, "hosts", self.host_with_component].get()

        self.assertEqual(response_list.status_code, HTTP_200_OK)
        self.assertEqual(response_list.json()["count"], 2)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service, role_name="Service Administrator"):
            response = self.client.v2[self.cluster_1, "hosts"].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertDictEqual(response_list.json()["results"][1], response.json()["results"][0])

            response = self.client.v2[self.cluster_1, "hosts", self.host_with_component].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertDictEqual(response_detail.json(), response.json())

    def test_adcm_5278_hosts_restriction_by_service_administrator_ownership_success(self):
        response_list = (self.client.v2 / "hosts").get()

        response_detail = self.client.v2[self.host_with_component].get()

        self.assertEqual(response_list.status_code, HTTP_200_OK)
        self.assertEqual(response_list.json()["count"], 2)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.service, role_name="Service Administrator"):
            response = (self.client.v2 / "hosts").get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertDictEqual(response_list.json()["results"][1], response.json()["results"][0])

            response = self.client.v2[self.host_with_component].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertDictEqual(response_detail.json(), response.json())


class TestAdvancedFilters(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        other_service = self.add_services_to_cluster(service_names=["service"], cluster=self.cluster_2).get()
        other_component = Component.objects.get(
            prototype__name="component", service=other_service, cluster=self.cluster_2
        )

        services = self.add_services_to_cluster(service_names=["service_1", "service_2"], cluster=self.cluster_1)
        self.service_1 = services.get(prototype__name="service_1", cluster=self.cluster_1)
        self.service_2 = services.get(prototype__name="service_2", cluster=self.cluster_1)

        self.component_1 = Component.objects.get(
            prototype__name="component_1", service=self.service_1, cluster=self.cluster_1
        )
        self.component_2 = Component.objects.get(
            prototype__name="component_2", service=self.service_1, cluster=self.cluster_1
        )
        self.component_3 = Component.objects.get(
            prototype__name="component_3", service=self.service_1, cluster=self.cluster_1
        )

        self.status_map = FullStatusMap(
            clusters={
                str(self.cluster_1.pk): {
                    "services": {
                        str(self.service_1.pk): {
                            "components": {
                                str(self.component_1.pk): {"status": 0},
                                str(self.component_2.pk): {"status": 16},
                                str(self.component_3.pk): {"status": 16},
                            },
                            "status": 16,
                            "details": [],
                        },
                        str(self.service_2.pk): {
                            "components": {},
                            "status": 0,
                            "details": [],
                        },
                    },
                    "status": 16,
                    "hosts": {},
                },
                str(self.cluster_2.pk): {
                    "services": {
                        str(other_service.pk): {
                            "components": {
                                str(other_component.pk): {"status": 0},
                            },
                            "status": 0,
                            "details": [],
                        }
                    },
                    "status": 0,
                    "hosts": {},
                },
            }
        )

    def test_filter_by_status__eq(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__eq": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_2.pk)

            with self.subTest("Filter value: bar"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__eq": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status__ieq(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: Down"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__ieq": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_1.pk)

            with self.subTest("Filter value: BaR"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__ieq": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status__ne(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__ne": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_1.pk)

            with self.subTest("Filter value: bar"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__ne": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

    def test_filter_by_status__ine(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: DoWn"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__ine": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_2.pk)

            with self.subTest("Filter value: BaR"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__ine": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

    def test_filter_by_status__in(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__in": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_2.pk)

            with self.subTest("Filter value: bar"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__in": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

            with self.subTest("Filter value: down,bar"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__in": "down,bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_1.pk)

    def test_filter_by_status__iin(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: DoWn"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__iin": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_1.pk)

            with self.subTest("Filter value: BaR"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__iin": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

            with self.subTest("Filter value: Up,BaR"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__iin": "Up,BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_2.pk)

    def test_filter_by_status__exclude(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__exclude": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_1.pk)

            with self.subTest("Filter value: bar"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__exclude": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

            with self.subTest("Filter value: down,bar"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__exclude": "down,bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_2.pk)

    def test_filter_by_status__iexclude(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: DoWn"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__iexclude": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_2.pk)

            with self.subTest("Filter value: BaR"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__iexclude": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

            with self.subTest("Filter value: Up,BaR"):
                response = self.client.v2[self.cluster_1, "services"].get(query={"status__iexclude": "Up,BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.service_1.pk)
