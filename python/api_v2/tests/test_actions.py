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

from collections.abc import Collection
from functools import partial
from operator import itemgetter
from typing import Literal, TypeAlias
import json

from cm.legacy.services.jinja_env import _get_action_info
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    ConcernCause,
    ConcernType,
    Host,
    HostComponent,
    JobLog,
    MaintenanceMode,
    ObjectType,
    Provider,
    Service,
    TaskLog,
)
from core.action import ExecutionStatus
from core.action.operations import ActionStartImpossibleReason
from core.cluster import ClusterService
from core.config import ConfigService
from core.types import ADCMCoreType, CoreObjectDescriptor, TaskID
from rbac.models import Role
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from tests.suites import SETUP_WITH_RBAC, ADCMDjangoAPISuite
from unittest_parametrize import parametrize

from api_v2.tests.base import APIV2Mixin, TestUtilsMixin
from api_v2.tests.helpers import create_bundle_and_prototype_rows

ObjectWithActions: TypeAlias = Cluster | Service | Component | Provider | Host


class TestActionsFiltering(ADCMDjangoAPISuite):
    suite_setup = SETUP_WITH_RBAC

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.cluster_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "cluster_actions")
        cls.cluster = cls.uc.add_cluster(cls.cluster_bundle, "Cluster with Actions")
        cls.service_1, *_ = cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cluster)
        cls.component_1 = Component.objects.get(service=cls.service_1, prototype__name="component_1")
        cls.component_2 = Component.objects.get(service=cls.service_1, prototype__name="component_2")
        cls.uc.add_services_to_cluster(names=["service_2"], cluster=cls.cluster)

        provider_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "provider_actions")
        cls.provider = cls.uc.add_provider(provider_bundle, "Provider with Actions")
        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="host-1")
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="host-2")

        cls.available_at_any = ["state_any"]
        common_at_created = [*cls.available_at_any, "state_created", "state_created_masking"]
        cls.available_at_created_no_multi = [
            *common_at_created,
            "multi_flag_unavailable",
            "state_created_available_multi_bag_unavailable",
        ]
        cls.available_at_created_flag = [
            *common_at_created,
            "multi_flag_masking",
            "state_created_available_multi_bag_unavailable",
        ]
        cls.available_at_created_bag = [
            *common_at_created,
            "multi_flag_unavailable",
            "state_created_available_multi_bag_available",
        ]

        common_at_installed = [
            *cls.available_at_any,
            "state_installed",
            "state_installed_masking",
            "state_created_unavailable",
        ]
        cls.available_at_installed_no_multi = [
            *common_at_installed,
            "multi_flag_unavailable",
            "state_created_unavailable_multi_bag_unavailable",
        ]
        cls.available_at_installed_flag = [
            *common_at_installed,
            "multi_flag_masking",
            "state_created_unavailable_multi_bag_unavailable",
        ]
        cls.available_at_installed_bag = [
            *common_at_installed,
            "multi_flag_unavailable",
            "state_created_unavailable_multi_bag_available",
        ]

        cls.installed_state = "installed"
        cls.flag_multi_state = "flag"
        cls.bag_multi_state = "bag"

    def assert_task_status_is(self, task_id: TaskID, status: str):
        task_status = TaskLog.objects.values_list("status", flat=True).get(id=task_id)
        self.assertEqual(task_status, status)

    def test_upgrading_status_host_remove_fail(self) -> None:
        self.add_host_to_cluster(self.cluster_1, self.host_1)
        self.cluster_1.set_state("upgrading")

        response = self.client.v2[self.cluster_1, "hosts", self.host_1].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_CONFLICT",
                "desc": "It is forbidden to delete host from cluster in upgrade mode",
                "level": "error",
            },
        )

    def test_upgrading_status_foreign_host_remove_fail(self) -> None:
        self.cluster_1.set_state("upgrading")

        response = self.client.v2[self.cluster_1, "hosts", self.host_1].delete()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_upgrading_status_service_remove_fail(self) -> None:
        service_1, *_ = self.uc.add_services_to_cluster(names=["service_1"], cluster=self.cluster_1)
        self.cluster_1.set_state("upgrading")
        self.cluster_1.before_upgrade["services"] = [
            service.prototype.name for service in Service.objects.filter(cluster=self.cluster_1)
        ]
        self.cluster_1.save()

        response = self.client.v2[service_1].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "SERVICE_CONFLICT",
                "desc": "Can't remove service when upgrading cluster",
                "level": "error",
            },
        )

    def test_upgrading_status_service_success(self) -> None:
        service_1, *_ = self.uc.add_services_to_cluster(names=["service_1"], cluster=self.cluster_1)
        self.cluster_1.set_state("upgrading")

        response = self.client.v2[service_1].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_upgrading_status_foreign_service_remove_fail(self) -> None:
        self.cluster_1.set_state("upgrading")
        self.cluster_1.before_upgrade["services"] = [
            service.prototype.name for service in Service.objects.filter(cluster=self.cluster_1)
        ]

        response = self.client.v2[self.cluster_1, "services", self.service_1].delete()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_filter_object_own_actions_success(self) -> None:
        for object_ in (self.cluster, self.service_1, self.component_1, self.provider, self.host_1):
            with self.subTest(msg=f"{object_.__class__.__name__} at different states"):
                self.check_object_action_list(object_=object_, expected_actions=self.available_at_created_no_multi)

                object_.set_multi_state(self.flag_multi_state)

                self.check_object_action_list(object_=object_, expected_actions=self.available_at_created_flag)

                object_.unset_multi_state(self.flag_multi_state)
                object_.set_multi_state(self.bag_multi_state)

                self.check_object_action_list(object_=object_, expected_actions=self.available_at_created_bag)

                object_.unset_multi_state(self.bag_multi_state)
                object_.set_state(self.installed_state)

                self.check_object_action_list(object_=object_, expected_actions=self.available_at_installed_no_multi)

                object_.set_multi_state(self.flag_multi_state)

                self.check_object_action_list(object_=object_, expected_actions=self.available_at_installed_flag)

                object_.unset_multi_state(self.flag_multi_state)
                object_.set_multi_state(self.bag_multi_state)

                self.check_object_action_list(object_=object_, expected_actions=self.available_at_installed_bag)

    def test_filter_host_actions_success(self) -> None:
        check_host_1_actions = partial(self.check_object_action_list, object_=self.host_1)
        check_host_2_actions = partial(self.check_object_action_list, object_=self.host_2)
        any_cluster = "from cluster any"
        any_all = (any_cluster, "from service any", "from component any")
        cluster_host_actions = ["cluster_host_action_allowed", "cluster_host_action_disallowed"]

        self.add_host_to_cluster(self.cluster, self.host_1)
        check_host_1_actions(expected_actions=[*self.available_at_created_no_multi, any_cluster, *cluster_host_actions])
        check_host_2_actions(expected_actions=self.available_at_created_no_multi)

        HostComponent.objects.create(
            cluster=self.cluster, host=self.host_1, service=self.service_1, component=self.component_1
        )
        check_host_1_actions(
            expected_actions=[*self.available_at_created_no_multi, *any_all, *cluster_host_actions * 3]
        )
        check_host_2_actions(expected_actions=self.available_at_created_no_multi)

        self.add_host_to_cluster(self.cluster, self.host_2)
        check_host_2_actions(expected_actions=[*self.available_at_created_no_multi, any_cluster, *cluster_host_actions])

        self.service_1.set_state(self.installed_state)
        check_host_1_actions(
            expected_actions=[
                *self.available_at_created_no_multi,
                *any_all,
                *cluster_host_actions * 3,
                "from service installed",
            ]
        )
        check_host_2_actions(expected_actions=[*self.available_at_created_no_multi, any_cluster, *cluster_host_actions])

        self.component_1.set_state(self.installed_state)
        self.component_1.set_multi_state(self.flag_multi_state)
        check_host_1_actions(
            expected_actions=[
                *self.available_at_created_no_multi,
                *any_all,
                "from service installed",
                "from component installed",
                "from component multi flag",
                *cluster_host_actions * 3,
            ]
        )
        check_host_2_actions(expected_actions=[*self.available_at_created_no_multi, any_cluster, *cluster_host_actions])

        self.cluster.set_state("woohoo")
        self.cluster.set_multi_state("flag")
        check_host_1_actions(
            expected_actions=[
                *self.available_at_created_no_multi,
                *any_all,
                "from cluster multi flag",
                "from service installed",
                "from component installed",
                "from component multi flag",
                *cluster_host_actions * 3,
            ]
        )
        check_host_2_actions(
            expected_actions=[
                *self.available_at_created_no_multi,
                any_cluster,
                "from cluster multi flag",
                *cluster_host_actions,
            ]
        )

    def test_filtering_success(self):
        action_to_filter = Action.objects.create(
            description="TEST DESCRIPTION 2",
            display_name="Test service action name",
            prototype=self.cluster.prototype,
            type="task",
            state_available="any",
            name="test_service_action_name",
            host_action=False,
        )
        self.add_host_to_cluster(self.cluster, self.host_1)
        filters = {
            "name": (action_to_filter.name, action_to_filter.name[1:-3].upper(), "wrong"),
            "displayName": (action_to_filter.display_name, action_to_filter.display_name[1:-3].upper(), "wrong"),
        }
        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            exact_items_found = 1
            partial_items_found = 1
            with self.subTest(filter_name=filter_name):
                response = self.client.v2[self.cluster, "actions"].get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(len(response.json()), exact_items_found)

                response = self.client.v2[self.cluster, "actions"].get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(len(response.json()), 0)

                if partial_value:
                    response = self.client.v2[self.cluster, "actions"].get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(len(response.json()), partial_items_found)

    def test_ordering_success(self):
        response = self.client.v2[self.cluster, "actions"].get(query={"ordering": "id"})
        expected_ids = [item["id"] for item in response.json()]
        self.assertListEqual(
            [action["id"] for action in response.json()],
            [
                action.pk
                for action in Action.objects.filter(prototype=self.cluster.prototype).order_by("id")
                if action.pk in expected_ids
            ],
        )

        response = self.client.v2[self.cluster, "actions"].get(query={"ordering": "-id"})
        expected_ids = [item["id"] for item in response.json()]
        self.assertListEqual(
            [action["id"] for action in response.json()],
            [
                action.pk
                for action in Action.objects.filter(prototype=self.cluster.prototype).order_by("-id")
                if action.pk in expected_ids
            ],
        )

    def test_adcm_4516_disallowed_host_action_not_executable_success(self) -> None:
        self.add_host_to_cluster(self.cluster, self.host_1)
        disallowed_action = Action.objects.filter(display_name="cluster_host_action_disallowed").first()
        self.check_object_action_list(
            object_=self.host_1,
            expected_actions=[
                *self.available_at_created_no_multi,
                "from cluster any",
                "cluster_host_action_allowed",
                "cluster_host_action_disallowed",
            ],
        )

        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save(update_fields=["maintenance_mode"])

        response = self.client.v2[self.host_1, "actions", disallowed_action, "run"].post(
            data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "TASK_ERROR",
                "desc": 'The Action is not available. One or more hosts in "Maintenance mode"',
                "level": "error",
            },
        )
        self.task_runner.expect_task_not_launched()

    def test_adcm_4535_job_cant_be_terminated_success(self) -> None:
        non_terminatable_status = ExecutionStatus.QUEUED

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        response = self.client.v2[self.host_1, "actions", allowed_action, "run"].post(
            data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        task_id = self.task_runner.expect_task_launched().id
        job = JobLog.objects.filter(task_id=task_id).first()
        job.status = non_terminatable_status
        job.save(update_fields=["status"])

        response = self.client.v2[job, "terminate"].post(data={})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "NOT_ALLOWED_TERMINATION",
                "desc": f"Job #{job.id} termination is not allowed due to status: {non_terminatable_status.value}",
                "level": "error",
            },
        )

    def test_adcm_4856_action_with_non_existing_component_fail(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        response = self.client.v2[self.host_1, "actions", allowed_action, "run"].post(
            data={
                "hostComponentMap": [{"hostId": self.host_1.pk, "componentId": 1000}],
                "config": {},
                "adcmMeta": {},
                "isVerbose": False,
            },
        )
        expected_response = {"code": "COMPONENT_NOT_FOUND", "desc": "component doesn't exist", "level": "error"}

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)
        self.task_runner.expect_task_not_launched()

    def test_adcm_4856_action_with_non_existing_host_fail(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        response = self.client.v2[self.host_1, "actions", allowed_action, "run"].post(
            data={
                "hostComponentMap": [{"hostId": 1000, "componentId": self.component_1.pk}],
                "config": {},
                "adcmMeta": {},
                "isVerbose": False,
            },
        )
        expected_response = {"code": "FOREIGN_HOST", "desc": "host is not belong to the cluster", "level": "error"}

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)
        self.task_runner.expect_task_not_launched()

    def test_adcm_4856_action_with_duplicated_hc_success(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        response = self.client.v2[self.host_1, "actions", allowed_action, "run"].post(
            data={
                "hostComponentMap": [
                    {"hostId": self.host_1.pk, "componentId": self.component_1.pk},
                    {"hostId": self.host_1.pk, "componentId": self.component_1.pk},
                ],
                "config": {},
                "adcmMeta": {},
                "isVerbose": False,
            },
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        task_id = self.task_runner.expect_task_launched().id
        self.task_runner.run_task(task_id)
        self.assert_task_status_is(task_id, "success")

    def test_adcm_4856_action_with_several_entries_hc_success(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        response = self.client.v2[self.host_1, "actions", allowed_action, "run"].post(
            data={
                "hostComponentMap": [
                    {"hostId": self.host_1.pk, "componentId": self.component_1.pk},
                    {"hostId": self.host_2.pk, "componentId": self.component_1.pk},
                    {"hostId": self.host_1.pk, "componentId": self.component_2.pk},
                ],
                "config": {},
                "adcmMeta": {},
                "isVerbose": False,
            },
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        task_id = self.task_runner.expect_task_launched().id
        self.task_runner.run_task(task_id)
        self.assert_task_status_is(task_id, "success")

    def test_adcm_5348_action_not_allowed_on_any_cluster_failed(self):
        test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        test_user = self.uc.create_user(**test_user_credentials)

        child_role_action = Role.objects.get(name="Cluster Action: action")
        child_role_clusters = Role.objects.get(name="View cluster configurations")
        cluster_as_cluster_one = self.uc.add_cluster(bundle=self.bundle_1, name="cluster_as_cluster_1")

        group_actions = create_group(
            name_to_display="Group for role `Cluster with Actions`", user_set=[{"id": test_user.pk}]
        )
        group_cluster_view = create_group(
            name_to_display="Group for role `View cluster configurations`", user_set=[{"id": test_user.pk}]
        )
        custom_role_in_policy_for_actions = role_create(
            display_name="Custom `Cluster with Actions` role", child=[child_role_action]
        )
        custom_role_in_policy_for_clusters = role_create(
            display_name="View cluster configurations", child=[child_role_clusters]
        )

        policy_create(
            name="Policy for role `Cluster with Actions`",
            role=custom_role_in_policy_for_actions,
            group=[group_actions],
            object=[self.cluster_1],
        )

        policy_create(
            name="View cluster configurations",
            role=custom_role_in_policy_for_clusters,
            group=[group_cluster_view],
            object=[self.cluster_1, self.cluster_2],
        )

        response = self.client.v2[cluster_as_cluster_one, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        self.client.login(**test_user_credentials)
        response = self.client.v2[cluster_as_cluster_one, "actions"].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def check_object_action_list(
        self, object_: Cluster | Service | Component | Provider | Host, expected_actions: list[str]
    ) -> None:
        response = self.client.v2[object_, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)

        data = response.json()
        self.assertTrue(isinstance(data, list))
        self.assertTrue(all("displayName" in entry for entry in data))
        actual_actions = sorted(entry["displayName"] for entry in data)
        self.assertListEqual(actual_actions, sorted(expected_actions))


class TestActionWithTemplates(ADCMDjangoAPISuite):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cluster_bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "cluster_actions_jinja")
        cls.cluster = cls.uc.add_cluster(cluster_bundle, "Cluster with Jinja Actions")
        cls.service_1, *_ = cls.uc.add_services_to_cluster(names=["first_service"], cluster=cls.cluster)
        cls.component_1 = Component.objects.get(service=cls.service_1, prototype__name="first_component")

    def test_group_jinja_config(self):
        cluster_bundle = self.uc.upload_bundle(self.test_bundles_dir / "cluster_action_with_group_jinja")
        cluster = self.uc.add_cluster(cluster_bundle, "Cluster with Jinja Actions 2")

        hosts = [self.uc.add_host(provider=self.provider, fqdn=f"host-{i}", cluster=cluster) for i in range(1, 15)]

        service, *_ = self.uc.add_services_to_cluster(names=["service_name"], cluster=cluster)

        component = service.components.get(prototype__name="server")
        self.uc.set_hostcomponent(
            cluster=cluster,
            entries=(
                (hosts[10], component),
                (hosts[9], component),
                (hosts[8], component),
                (hosts[7], component),
                (hosts[6], component),
                (hosts[5], component),
                (hosts[4], component),
                (hosts[3], component),
                (hosts[2], component),
                (hosts[1], component),
                (hosts[1], component),
            ),
        )

        for host in hosts[8:12][::-1]:
            response = (self.client.v2 / "hosts" / host.pk / "maintenance-mode").post(
                data={"maintenanceMode": "on"},
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

        action = Action.objects.get(name="test_action_group")
        response = self.client.v2[cluster, "actions", action.pk].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            response.json()["configuration"]["config"]["group"],
            ["host-1", "host-2", "host-3", "host-4", "host-5", "host-6", "host-7", "host-8", "host-13", "host-14"],
        )

    def test_retrieve_jinja_config(self):
        action = Action.objects.filter(name="check_state", prototype=self.cluster.prototype).first()

        response = self.client.v2[self.cluster, "actions", action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        configuration = response.json()["configuration"]
        self.assertSetEqual(set(configuration.keys()), {"configSchema", "config", "adcmMeta"})
        expected_schema = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_action_with_jinja_config.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertDictEqual(configuration["configSchema"], expected_schema)
        self.assertDictEqual(
            configuration["config"],
            {"activatable_group": {"text": "text"}, "boolean": True, "boolean1": False, "float": 2.0},
        )
        self.assertDictEqual(configuration["adcmMeta"], {"/activatable_group": {"isActive": True}})

    def test_adcm_6013_jinja_config_with_min_max(self):
        action = Action.objects.get(name="check_numeric_min_max_param", prototype=self.cluster.prototype)

        response = self.client.v2[self.cluster, "actions", action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        expected_response = json.loads(
            (
                self.test_files_dir / "responses" / "config_schemas" / "for_action_with_numeric_min_max_param.json"
            ).read_text(encoding="utf-8")
        )
        expected_response["id"] = action.id
        self.assertDictEqual(response.json(), expected_response)

        self.cluster.set_state(state="ready_for_numeric_min_max")
        response = self.client.v2[self.cluster, "actions", action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        expected_response = json.loads(
            (
                self.test_files_dir
                / "responses"
                / "config_schemas"
                / "for_action_with_numeric_min_max_param_target_state.json"
            ).read_text(encoding="utf-8")
        )
        expected_response["id"] = action.id
        self.assertDictEqual(response.json(), expected_response)

    def test_adcm_4703_action_retrieve_returns_500(self) -> None:
        for object_ in (self.cluster, self.service_1, self.component_1):
            with self.subTest(object_.__class__.__name__):
                response = self.client.v2[object_, "actions"].get()
                self.assertEqual(response.status_code, HTTP_200_OK)

                for action_id in map(itemgetter("id"), response.json()):
                    response = self.client.v2[object_, "actions", action_id].get()
                    self.assertEqual(response.status_code, HTTP_200_OK)

    def test_get_action_info_success(self) -> None:
        for object_, group in (
            (self.cluster, "CLUSTER"),
            (self.service_1, self.service_1.name),
            (self.component_1, f"{self.component_1.service.name}.{self.component_1.name}"),
        ):
            action = Action.objects.filter(name="check_state", prototype=object_.prototype).get()
            self.assertDictEqual(_get_action_info(action=action), {"name": "check_state", "owner_group": group})

    def test_adcm_8330_conflicting_params(self) -> None:
        # an ansible script's own (arbitrary) params must not be confused with reserved
        # internal-script param names during job retrieval on run, for both static and
        # jinja-rendered scripts
        expected_params = {
            "ansible_tags": "ok",
            "operation": ["a", "b"],
            "services": "very nice, awesome",
            "rules": "not-a-list",
            "changes": "not-a-list",
        }

        for action_name, script_name in (
            ("adcm_8330_conflicting_params", "adcm_8330_conflicting_params"),
            ("adcm_8330_conflicting_params_jinja", "adcm_8330_conflicting_params_script"),
        ):
            with self.subTest(action_name):
                action = Action.objects.get(name=action_name, prototype=self.cluster.prototype)

                response = self.client.v2[self.cluster, "actions", action, "run"].post()

                self.assertEqual(response.status_code, HTTP_200_OK)
                task_id = self.task_runner.expect_task_launched().id
                self.task_runner.run_task(task_id)

                self.assertEqual(TaskLog.objects.values_list("status", flat=True).get(id=task_id), "success")
                self.assertDictEqual(
                    JobLog.objects.filter(task_id=task_id).values_list("params", flat=True).get(name=script_name),
                    expected_params,
                )


class TestAction(ADCMDjangoAPISuite):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.action_with_config = Action.objects.get(name="with_config", prototype=cls.cluster_1.prototype)
        bundle = cls.uc.upload_bundle(cls.test_bundles_dir / "cluster_import_upgrade")
        cls.cluster = cls.uc.add_cluster(bundle=bundle, name="cluster_with_revert_actions")
        cls.unsupported_bundle, _ = create_bundle_and_prototype_rows(
            [
                {
                    "contract_version": "0.999",
                    "name": "unsupported_bundle",
                    "display_name": "Unsupported Cluster",
                    "version": "1.0.0",
                    "obj_type": ObjectType.CLUSTER,
                }
            ]
        )[0]

    def test_retrieve_with_config(self):
        response = self.client.v2[self.cluster_1, "actions", self.action_with_config].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        configuration = response.json()["configuration"]
        self.assertSetEqual(set(configuration.keys()), {"configSchema", "config", "adcmMeta"})
        expected_schema = json.loads(
            (self.test_files_dir / "responses" / "config_schemas" / "for_action_with_config.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertDictEqual(configuration["configSchema"], expected_schema)
        self.assertDictEqual(
            configuration["config"],
            {
                "activatable_group": {"text": "text"},
                "after": ["1", "woohoo"],
                "grouped": {"second": 4.3, "simple": 4},
                "simple": None,
            },
        )
        self.assertDictEqual(configuration["adcmMeta"], {"/activatable_group": {"isActive": True}})

    def test_run_non_blocking(self) -> None:
        action = Action.objects.get(name="action", prototype=self.cluster_1.prototype)

        response = self.client.v2[self.cluster_1, "actions", action, "run"].post(data={"shouldBlockObject": False})

        self.assertEqual(response.status_code, HTTP_200_OK)

        launched_task_id = self.task_runner.expect_task_launched().id
        task = TaskLog.objects.get(id=launched_task_id)

        self.assertIsNone(task.lock)

        self.assertEqual(self.cluster_1.concerns.count(), 1)
        first_concern = self.cluster_1.concerns.get()
        self.assertEqual(first_concern.type, ConcernType.FLAG)
        self.assertEqual(first_concern.cause, ConcernCause.JOB)

        with self.subTest("Same action can not be launched"):
            response = self.client.v2[self.cluster_1, "actions", action, "run"].post()
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        with self.subTest("Another action can be launched"):
            response = self.client.v2[self.cluster_1, "actions", self.action_with_config].get()
            configuration = response.json()["configuration"]

            response = self.client.v2[self.cluster_1, "actions", self.action_with_config, "run"].post(
                data={"configuration": {"config": configuration["config"], "adcmMeta": configuration["adcmMeta"]}}
            )

            self.assertEqual(response.status_code, HTTP_200_OK)

            self.assertEqual(self.cluster_1.concerns.count(), 2)
            self.assertEqual(self.cluster_1.concerns.filter(type=ConcernType.FLAG).count(), 1)
            self.assertEqual(self.cluster_1.concerns.filter(type=ConcernType.LOCK).count(), 1)

    def test_adcm_7841_variant_in_config(self) -> None:
        """
        `{type: variant, source: {type: config, name: <field_name>}}` fields should consider
        only owner's config as variant values source.
        Absence of <field_name> in action's config should not lead to error.
        """
        bundle = self.uc.upload_bundle(self.test_bundles_dir / "cluster_actions")
        cluster = self.uc.add_cluster(bundle=bundle, name="cluster_with_actions")
        action = Action.objects.get(name="with_variant_in_config", prototype=cluster.prototype)

        cluster.state = "ready_for_variant"
        cluster.save(update_fields=["state"])

        payload = {"configuration": {"config": {"variant_from_config": "cluster_entry1"}, "adcmMeta": {}}}
        response = self.client.v2[cluster, "actions", action, "run"].post(data=payload)

        self.assertEqual(response.status_code, HTTP_200_OK)

    def set_unsupported_bundle_before_upgrade(self, cluster: Cluster, unsupported_bundle_id: int) -> None:
        cluster.before_upgrade = {"bundle_id": unsupported_bundle_id}
        cluster.save(update_fields=["before_upgrade"])

    @parametrize(
        ("case", "action"),
        [
            ("scripts_template", "revert_template"),
            ("scripts", "revert"),
        ],
    )
    def test_action_revert_on_unsupported_bundle_fail(self, case: str, action: str) -> None:
        with self.subTest(case=case):
            self.set_unsupported_bundle_before_upgrade(self.cluster, self.unsupported_bundle.pk)
            action = Action.objects.get(name=action, prototype=self.cluster.prototype)

            response = self.client.v2[self.cluster, "actions", action, "run"].post()

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["desc"], f"Can't run {action.display_name} to unsupported bundle")


class TestActionHCMapping(ADCMDjangoAPISuite, APIV2Mixin, TestUtilsMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cluster_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_one")
        cls.cluster_1 = cls.uc.add_cluster(bundle=cluster_bundle, name="Test cluster for hc_acl action")
        cls.service_1 = cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cluster_1)[0]
        cls.component_1 = Component.objects.get(prototype__name="component_1", service=cls.service_1)
        cls.component_2 = Component.objects.get(prototype__name="component_2", service=cls.service_1)

        provider_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "provider")
        provider = cls.uc.add_provider(bundle=provider_bundle, name="provider")
        cls.host_1 = cls.uc.add_host(provider=provider, name="host-1", cluster=cls.cluster_1)
        cls.host_2 = cls.uc.add_host(provider=provider, name="host-2", cluster=cls.cluster_1)

        cls.action = Action.objects.get(name="with_hc", prototype_id=cls.cluster_1.prototype_id)

    def run_task(
        self,
        object_: Cluster | Service | Component | Provider | Host | ActionHostGroup,
        action: Action,
        mapping: Collection[tuple[Host, Component]] = (),
        config: dict[Literal["config", "adcmMeta"], dict] | None = None,
        expected_code: int = HTTP_200_OK,
    ) -> None:
        hc = {"hostComponentMap": [{"hostId": host.id, "componentId": component.id} for host, component in mapping]}
        config = config or {"config": {}, "adcmMeta": {}}

        response = self.client.v2[object_, "actions", action, "run"].post(data={"isVerbose": False, **config, **hc})

        self.assertEqual(response.status_code, expected_code, f"Unexpected run result: {response.status_code}")

    def get_launched_task_mapping(self):
        task_id = self.task_runner.expect_task_launched().id
        return TaskLog.objects.values_list("hostcomponentmap", flat=True).get(id=task_id)

    def test_adcm_7530_simple_add_remove_success(self):
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_1, self.component_2),))
        self.check_mm_is_on_only_for(
            obj=None, cluster_id=self.cluster_1.id, cluster_service=self.container.get(ClusterService)
        )

        self.run_task(object_=self.cluster_1, action=self.action, mapping=((self.host_2, self.component_1),))

        self.assertDictEqual(
            self.get_launched_task_mapping(),
            {
                "add": {str(self.component_1.id): [self.host_2.id]},
                "remove": {str(self.component_2.id): [self.host_1.id]},
            },
        )

    def test_adcm_7530_add_host_in_mm_fail(self):
        self.set_maintenance_mode(obj=self.host_1, value=MaintenanceMode.ON)

        self.check_mm_is_on_only_for(
            obj=self.host_1, cluster_id=self.cluster_1.id, cluster_service=self.container.get(ClusterService)
        )
        self.run_task(
            object_=self.cluster_1,
            action=self.action,
            mapping=((self.host_1, self.component_1),),
            expected_code=HTTP_409_CONFLICT,
        )
        self.task_runner.expect_task_not_launched()

    def test_adcm_7530_remove_host_in_mm_success(self):
        self.create_mapping(
            cluster=self.cluster_1, entries=((self.host_1, self.component_2), (self.host_2, self.component_2))
        )
        self.set_maintenance_mode(obj=self.host_2, value=MaintenanceMode.ON)
        self.check_mm_is_on_only_for(
            obj=self.host_2, cluster_id=self.cluster_1.id, cluster_service=self.container.get(ClusterService)
        )

        self.run_task(object_=self.cluster_1, action=self.action, mapping=((self.host_1, self.component_2),))

        self.assertDictEqual(
            self.get_launched_task_mapping(), {"add": {}, "remove": {str(self.component_2.id): [self.host_2.id]}}
        )

    def test_adcm_7530_component_mm_does_not_affects_remove_mapping_success(self):
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_1, self.component_2),))
        self.set_maintenance_mode(obj=self.component_2, value=MaintenanceMode.ON)
        self.check_mm_is_on_only_for(
            obj=self.component_2, cluster_id=self.cluster_1.id, cluster_service=self.container.get(ClusterService)
        )

        self.run_task(object_=self.cluster_1, action=self.action, mapping=((self.host_2, self.component_1),))

        self.assertDictEqual(
            self.get_launched_task_mapping(),
            {
                "add": {str(self.component_1.id): [self.host_2.id]},
                "remove": {str(self.component_2.id): [self.host_1.id]},
            },
        )

    def test_adcm_7530_component_mm_does_not_affects_add_mapping_success(self):
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_1, self.component_2),))
        self.set_maintenance_mode(obj=self.component_1, value=MaintenanceMode.ON)
        self.check_mm_is_on_only_for(
            obj=self.component_1, cluster_id=self.cluster_1.id, cluster_service=self.container.get(ClusterService)
        )

        self.run_task(object_=self.cluster_1, action=self.action, mapping=((self.host_2, self.component_1),))

        self.assertDictEqual(
            self.get_launched_task_mapping(),
            {
                "add": {str(self.component_1.id): [self.host_2.id]},
                "remove": {str(self.component_2.id): [self.host_1.id]},
            },
        )

    def test_adcm_7530_service_state_does_not_affects_success(self):
        self.create_mapping(cluster=self.cluster_1, entries=((self.host_1, self.component_2),))

        self.service_1.state = "not created"
        self.service_1.save(update_fields=["state"])
        self.check_mm_is_on_only_for(
            obj=None, cluster_id=self.cluster_1.id, cluster_service=self.container.get(ClusterService)
        )

        self.run_task(object_=self.cluster_1, action=self.action, mapping=((self.host_2, self.component_1),))

        self.assertDictEqual(
            self.get_launched_task_mapping(),
            {
                "add": {str(self.component_1.id): [self.host_2.id]},
                "remove": {str(self.component_2.id): [self.host_1.id]},
            },
        )


class TestActionStartImpossibleReason(ADCMDjangoAPISuite):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.msg_services_in_mm = ActionStartImpossibleReason.MAINTENANCE_MODE.value.format(
            entity_type="Action", violator_type="services"
        )
        cls.msg_components_in_mm = ActionStartImpossibleReason.MAINTENANCE_MODE.value.format(
            entity_type="Action", violator_type="components"
        )
        cls.msg_hosts_in_mm = ActionStartImpossibleReason.MAINTENANCE_MODE.value.format(
            entity_type="Action", violator_type="hosts"
        )
        cls.msg_ldap_settings = ActionStartImpossibleReason.LDAP_OFF.value

        cls.cluster_action = Action.objects.get(name="action", prototype=cls.cluster_1.prototype)
        cls.provider_action = Action.objects.get(name="provider_action", prototype=cls.provider.prototype)

        service_names = {"service_1", "service_1_clone"}
        cls.uc.add_services_to_cluster(names=list(service_names), cluster=cls.cluster_1)
        # to be sure MM distribution is correct
        assert (  # noqa: S101
            set(Service.objects.filter(cluster=cls.cluster_1).values_list("prototype__name", flat=True))
            == service_names
        )

        cls.service = Service.objects.get(prototype__name="service_1", cluster=cls.cluster_1)
        cls.service_action = Action.objects.get(name="action", prototype=cls.service.prototype)

        cls.component_1 = Component.objects.get(prototype__name="component_1", service=cls.service)
        cls.component_1_action = Action.objects.get(name="action_1_comp_1", prototype=cls.component_1.prototype)

        cls.component_2 = Component.objects.get(prototype__name="component_2", service=cls.service)
        cls.component_3 = Component.objects.get(prototype__name="component_3", service=cls.service)
        # to be sure MM distribution is correct
        assert set(Component.objects.filter(service=cls.service).values_list("id", flat=True)) == {  # noqa: S101
            cls.component_1.id,
            cls.component_2.id,
            cls.component_3.id,
        }

        cls.host_1 = cls.uc.add_host(fqdn="test-host-1", provider=cls.provider, cluster=cls.cluster_1)
        cls.host_1_action = Action.objects.get(name="host_action", prototype=cls.host_1.prototype)
        cls.host_2 = cls.uc.add_host(fqdn="test-host-2", provider=cls.provider, cluster=cls.cluster_1)
        cls.host_3 = cls.uc.add_host(fqdn="test-host-3", provider=cls.provider, cluster=cls.cluster_1)
        cls.host_4 = cls.uc.add_host(fqdn="test-host-4", provider=cls.provider, cluster=cls.cluster_1)

        cls.free_host = cls.uc.add_host(fqdn="test-host-free", provider=cls.provider, cluster=cls.cluster_1)
        cls.free_host_action = Action.objects.get(name="host_action", prototype=cls.free_host.prototype)

        cls.control_service = Service.objects.get(prototype__name="service_1_clone", cluster=cls.cluster_1)
        cls.control_component = Component.objects.get(prototype__name="component_1", service=cls.control_service)
        cls.control_host = cls.uc.add_host(fqdn="test-host-control", provider=cls.provider, cluster=cls.cluster_1)

        cls.adcm = ADCM.objects.get()
        cls.adcm_action = Action.objects.get(name="run_ldap_sync", prototype=cls.adcm.prototype)

        cls.uc.set_hostcomponent(
            cluster=cls.cluster_1,
            entries=(
                (cls.host_1, cls.component_1),
                (cls.host_2, cls.component_1),
                (cls.host_3, cls.component_2),
                (cls.host_4, cls.component_2),
                (cls.control_host, cls.control_component),
            ),
        )

        cls.cluster_ahg = cls.uc.create_action_host_group(owner=cls.cluster_1, name="cluster_ahg")
        cls.uc.add_hosts_to_action_host_group(group_id=cls.cluster_ahg.pk, hosts=[cls.host_1.pk])

        cls.service_ahg = cls.uc.create_action_host_group(owner=cls.service, name="service_ahg")
        cls.uc.add_hosts_to_action_host_group(group_id=cls.service_ahg.pk, hosts=[cls.host_2.pk])

        cls.component_ahg = cls.uc.create_action_host_group(owner=cls.component_2, name="component_ahg")
        cls.uc.add_hosts_to_action_host_group(group_id=cls.component_ahg.pk, hosts=[cls.host_3.pk])
        cls.component_2_action = Action.objects.get(name="action_1_comp_2", prototype=cls.component_2.prototype)

        cls.action_from_cluster = Action.objects.get(
            name="cluster_on_host", prototype=cls.cluster_1.prototype, host_action=True
        )
        cls.action_from_service = Action.objects.get(
            name="service_on_host", prototype=cls.service.prototype, host_action=True
        )
        cls.action_from_component = Action.objects.get(
            name="component_on_host", prototype=cls.component_1.prototype, host_action=True
        )

    @parametrize(
        ("in_mm", "target", "action", "expected_msg"),
        [
            # suite_name, (objects_in_mm, ...), action_target, action, start_impossible_reason
            # suite1: not mapped host in cluster in mm
            (("free_host",), "cluster_1", "cluster_action", "msg_hosts_in_mm"),
            (("free_host",), "service", "service_action", None),
            (("free_host",), "component_1", "component_1_action", None),
            (("free_host",), "host_1", "host_1_action", None),
            (("free_host",), "free_host", "free_host_action", "msg_hosts_in_mm"),
            # suite2: one of two hosts on component in mm
            (("host_2",), "cluster_1", "cluster_action", "msg_hosts_in_mm"),
            (("host_2",), "service", "service_action", "msg_hosts_in_mm"),
            (("host_2",), "component_1", "component_1_action", "msg_hosts_in_mm"),
            (("host_2",), "host_1", "host_1_action", None),
            (("host_2",), "free_host", "free_host_action", None),
            # suite3: host in second service in mm (indirect second service in MM)
            (("control_host",), "cluster_1", "cluster_action", "msg_services_in_mm"),
            (("control_host",), "service", "service_action", None),
            (("control_host",), "component_1", "component_1_action", None),
            (("control_host",), "host_1", "host_1_action", None),
            (("control_host",), "free_host", "free_host_action", None),
            # suite4: host in second component in mm
            (("host_3",), "cluster_1", "cluster_action", "msg_hosts_in_mm"),
            (("host_3",), "service", "service_action", "msg_hosts_in_mm"),
            (("host_3",), "component_1", "component_1_action", None),
            (("host_3",), "host_1", "host_1_action", None),
            (("host_3",), "free_host", "free_host_action", None),
            # suite5: all component hosts in mm (indirect component in MM)
            (("host_1", "host_2"), "cluster_1", "cluster_action", "msg_components_in_mm"),
            (("host_1", "host_2"), "service", "service_action", "msg_components_in_mm"),
            (
                ("host_1", "host_2"),
                "component_1",
                "component_1_action",
                "msg_components_in_mm",
            ),
            (("host_1", "host_2"), "host_1", "host_1_action", "msg_hosts_in_mm"),
            (("host_1", "host_2"), "free_host", "free_host_action", None),
            # suite6: one of components in mm
            (("component_1",), "cluster_1", "cluster_action", "msg_components_in_mm"),
            (("component_1",), "service", "service_action", "msg_components_in_mm"),
            (("component_1",), "component_1", "component_1_action", "msg_components_in_mm"),
            (("component_1",), "host_1", "host_1_action", None),
            (("component_1",), "free_host", "free_host_action", None),
            # suite7: all components in mm (indirect service in MM)
            (
                ("component_1", "component_2", "component_3"),
                "cluster_1",
                "cluster_action",
                "msg_services_in_mm",
            ),
            (
                ("component_1", "component_2", "component_3"),
                "service",
                "service_action",
                "msg_services_in_mm",
            ),
            (
                ("component_1", "component_2", "component_3"),
                "component_1",
                "component_1_action",
                "msg_components_in_mm",
            ),
            (("component_1", "component_2", "component_3"), "host_1", "host_1_action", None),
            (
                ("component_1", "component_2", "component_3"),
                "free_host",
                "free_host_action",
                None,
            ),
            # suite8: service in mm
            (("service",), "cluster_1", "cluster_action", "msg_services_in_mm"),
            (("service",), "service", "service_action", "msg_services_in_mm"),
            (("service",), "component_1", "component_1_action", "msg_components_in_mm"),
            (("service",), "host_1", "host_1_action", None),
            (("service",), "free_host", "free_host_action", None),
            # suite9: host_action, host (target) in MM
            (("host_1",), "host_1", "host_1_action", "msg_hosts_in_mm"),
            (("host_1",), "host_1", "action_from_cluster", "msg_hosts_in_mm"),
            (("host_1",), "host_1", "action_from_service", "msg_hosts_in_mm"),
            (("host_1",), "host_1", "action_from_component", "msg_hosts_in_mm"),
            # suite10: host_action, service in MM
            (("service",), "host_1", "host_1_action", None),
            (("service",), "host_1", "action_from_cluster", None),
            (("service",), "host_1", "action_from_service", None),
            (("service",), "host_1", "action_from_component", None),
            # suite11: host_action, component in MM
            (("component_1",), "host_1", "host_1_action", None),
            (("component_1",), "host_1", "action_from_cluster", None),
            (("component_1",), "host_1", "action_from_service", None),
            (("component_1",), "host_1", "action_from_component", None),
            # suite12: host_action, host (target) and one other object in MM
            (("host_1", "service"), "host_1", "host_1_action", "msg_hosts_in_mm"),
            (
                ("host_1", "service"),
                "host_1",
                "action_from_cluster",
                "msg_hosts_in_mm",
            ),
            (
                ("host_1", "service"),
                "host_1",
                "action_from_service",
                "msg_hosts_in_mm",
            ),
            (
                ("host_1", "service"),
                "host_1",
                "action_from_component",
                "msg_hosts_in_mm",
            ),
            (
                ("host_1", "component_1"),
                "host_1",
                "host_1_action",
                "msg_hosts_in_mm",
            ),
            (
                ("host_1", "component_1"),
                "host_1",
                "action_from_cluster",
                "msg_hosts_in_mm",
            ),
            (
                ("host_1", "component_1"),
                "host_1",
                "action_from_service",
                "msg_hosts_in_mm",
            ),
            (
                ("host_1", "component_1"),
                "host_1",
                "action_from_component",
                "msg_hosts_in_mm",
            ),
            # suite13: actions on AHG
            (("host_1",), "cluster_ahg", "cluster_action", "msg_hosts_in_mm"),
            (("service",), "cluster_ahg", "cluster_action", "msg_services_in_mm"),
            (("component_1",), "cluster_ahg", "cluster_action", "msg_components_in_mm"),
            (("host_1",), "service_ahg", "service_action", "msg_hosts_in_mm"),
            (("service",), "service_ahg", "service_action", "msg_services_in_mm"),
            (("component_1",), "service_ahg", "service_action", "msg_components_in_mm"),
            (("host_3",), "component_ahg", "component_2_action", "msg_hosts_in_mm"),
            (("service",), "component_ahg", "component_2_action", "msg_components_in_mm"),
            (
                ("component_2",),
                "component_ahg",
                "component_2_action",
                "msg_components_in_mm",
            ),
        ],
        ids=[
            "suite1_cluster_action",
            "suite1_service_action",
            "suite1_component_action",
            "suite1_action_on_host",
            "suite1_action_on_free_host",
            "suite2_cluster_action",
            "suite2_service_action",
            "suite2_component_action",
            "suite2_action_on_host",
            "suite2_action_on_free_host",
            "suite3_cluster_action",
            "suite3_service_action",
            "suite3_component_action",
            "suite3_action_on_host",
            "suite3_action_on_free_host",
            "suite4_cluster_action",
            "suite4_service_action",
            "suite4_component_action",
            "suite4_action_on_host",
            "suite4_action_on_free_host",
            "suite5_cluster_action",
            "suite5_service_action",
            "suite5_component_action",
            "suite5_action_on_host",
            "suite5_action_on_free_host",
            "suite6_cluster_action",
            "suite6_service_action",
            "suite6_component_action",
            "suite6_action_on_host",
            "suite6_action_on_free_host",
            "suite7_cluster_action",
            "suite7_service_action",
            "suite7_component_action",
            "suite7_action_on_host",
            "suite7_action_on_free_host",
            "suite8_cluster_action",
            "suite8_service_action",
            "suite8_component_action",
            "suite8_action_on_host",
            "suite8_action_on_free_host",
            "suite9_host_1_action",
            "suite9_action_from_cluster",
            "suite9_action_from_service",
            "suite9_action_from_component",
            "suite10_host_1_action",
            "suite10_action_from_cluster",
            "suite10_action_from_service",
            "suite10_action_from_component",
            "suite11_host_1_action",
            "suite11_action_from_cluster",
            "suite11_action_from_service",
            "suite11_action_from_component",
            "suite12_host_1_action_service",
            "suite12_action_from_cluster_service",
            "suite12_action_from_service_service",
            "suite12_action_from_component_service",
            "suite12_host_1_action_component_1",
            "suite12_action_from_cluster_component_1",
            "suite12_action_from_service_component_1",
            "suite12_action_from_component_component_1",
            "suite13_clAHG_host_1",
            "suite13_clAHG_service",
            "suite13_clAHG_component_1",
            "suite13_seAHG_host_1",
            "suite13_seAHG_service",
            "suite13_seAHG_component_1",
            "suite13_coAHG_host_3",
            "suite13_coAHG_service",
            "suite13_coAHG_component_2",
        ],
    )
    def test_sir_cluster(self, in_mm: tuple[str, ...], target: str, action: str, expected_msg: str):
        for object_in_mm_name in in_mm:
            self.set_mm(object_=getattr(self, object_in_mm_name), value="on")

        self.check_start_impossible_reason(
            object_=getattr(self, target),
            action=getattr(self, action),
            expected_sir=getattr(self, expected_msg) if expected_msg else None,
        )

    @parametrize("all_provider_hosts_in_mm", [True, False], ids=["true", "false"])
    def test_sir_provider(self, all_provider_hosts_in_mm):
        if all_provider_hosts_in_mm:
            for host in Host.objects.filter(provider=self.provider):
                self.set_mm(object_=host, value="on")

        self.check_start_impossible_reason(object_=self.provider, action=self.provider_action)

    def test_sir_adcm(self):
        config_service = self.container.get(ConfigService)
        current_config = config_service.retrieve_current_configuration(
            owner=CoreObjectDescriptor(id=self.adcm.pk, type=ADCMCoreType.ADCM)
        )
        post_data = {
            "config": current_config.values,
            "adcmMeta": {k: {"isActive": v.is_active} for k, v in current_config.attributes.items()},
        }
        post_data["config"]["global"]["adcm_url"] = "test"

        response = self.client.v2[self.adcm, "configs"].post(data=post_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_start_impossible_reason(
            object_=self.adcm,
            action=self.adcm_action,
            expected_sir=self.msg_ldap_settings,
        )

        post_data["config"]["ldap_integration"]["ldap_uri"] = "test"
        post_data["config"]["ldap_integration"]["ldap_user"] = "test"
        post_data["config"]["ldap_integration"]["ldap_password"] = "test"
        post_data["config"]["ldap_integration"]["user_search_base"] = "test"
        post_data["adcmMeta"]["/ldap_integration"]["isActive"] = True

        response = self.client.v2[self.adcm, "configs"].post(data=post_data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_start_impossible_reason(object_=self.adcm, action=self.adcm_action)

    def check_start_impossible_reason(
        self,
        object_: Cluster | Service | Component | Host,
        action: Action,
        expected_sir: str | None = None,
    ):
        if action.host_action:
            list_endpoint = self.client.v2[object_.cluster, "hosts", object_, "actions"]
        else:
            list_endpoint = self.client.v2[object_, "actions"]
        retrieve_endpoint = list_endpoint / action
        run_endpoint = retrieve_endpoint / "run"

        list_response = list_endpoint.get()
        self.assertEqual(list_response.status_code, HTTP_200_OK)
        target_action = [act for act in list_response.json() if act["id"] == action.id][0]
        self.assertEqual(target_action["startImpossibleReason"], expected_sir)

        retrieve_response = retrieve_endpoint.get()
        self.assertEqual(retrieve_response.status_code, HTTP_200_OK)
        self.assertEqual(retrieve_response.json()["startImpossibleReason"], expected_sir)

        run_response = run_endpoint.post()
        if expected_sir:
            self.assertEqual(run_response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(run_response.json()["desc"], expected_sir)
        else:
            self.assertEqual(run_response.status_code, HTTP_200_OK)

    def set_mm(self, object_: Service | Component | Host, value: Literal["on", "off"]):
        response = self.client.v2[object_, "maintenance-mode"].post(data={"maintenanceMode": value})
        self.assertEqual(response.status_code, HTTP_200_OK)
