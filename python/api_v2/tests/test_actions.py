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

from functools import partial
from operator import itemgetter
from typing import TypeAlias
from unittest.mock import patch
import json

from cm.models import (
    Action,
    Cluster,
    Component,
    ConcernCause,
    ConcernType,
    Host,
    HostComponent,
    JobLog,
    MaintenanceMode,
    Provider,
    Service,
)
from cm.services.jinja_env import _get_action_info
from cm.tests.mocks.task_runner import RunTaskMock
from rbac.models import Role
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase

ObjectWithActions: TypeAlias = Cluster | Service | Component | Provider | Host


class TestActionsFiltering(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_bundle = self.add_bundle(self.test_bundles_dir / "cluster_actions")
        self.cluster = self.add_cluster(self.cluster_bundle, "Cluster with Actions")
        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster).get()
        self.component_1: Component = Component.objects.get(service=self.service_1, prototype__name="component_1")
        self.component_2: Component = Component.objects.get(service=self.service_1, prototype__name="component_2")
        self.add_services_to_cluster(service_names=["service_2"], cluster=self.cluster)

        provider_bundle = self.add_bundle(self.test_bundles_dir / "provider_actions")
        self.provider = self.add_provider(provider_bundle, "Provider with Actions")
        self.host_1 = self.add_host(provider=self.provider, fqdn="host-1")
        self.host_2 = self.add_host(provider=self.provider, fqdn="host-2")

        self.available_at_any = ["state_any"]
        common_at_created = [*self.available_at_any, "state_created", "state_created_masking"]
        self.available_at_created_no_multi = [
            *common_at_created,
            "multi_flag_unavailable",
            "state_created_available_multi_bag_unavailable",
        ]
        self.available_at_created_flag = [
            *common_at_created,
            "multi_flag_masking",
            "state_created_available_multi_bag_unavailable",
        ]
        self.available_at_created_bag = [
            *common_at_created,
            "multi_flag_unavailable",
            "state_created_available_multi_bag_available",
        ]

        common_at_installed = [
            *self.available_at_any,
            "state_installed",
            "state_installed_masking",
            "state_created_unavailable",
        ]
        self.available_at_installed_no_multi = [
            *common_at_installed,
            "multi_flag_unavailable",
            "state_created_unavailable_multi_bag_unavailable",
        ]
        self.available_at_installed_flag = [
            *common_at_installed,
            "multi_flag_masking",
            "state_created_unavailable_multi_bag_unavailable",
        ]
        self.available_at_installed_bag = [
            *common_at_installed,
            "multi_flag_unavailable",
            "state_created_unavailable_multi_bag_available",
        ]

        self.installed_state = "installed"
        self.flag_multi_state = "flag"
        self.bag_multi_state = "bag"

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
        service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
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
        service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
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

        with RunTaskMock() as run_task:
            response = self.client.v2[self.host_1, "actions", disallowed_action, "run"].post(
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "ACTION_ERROR",
                "desc": "The Action is not available. Host in 'Maintenance mode'",
                "level": "error",
            },
        )
        # run task shouldn't be called
        self.assertIsNone(run_task.target_task)

    def test_adcm_4535_job_cant_be_terminated_success(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        with RunTaskMock() as run_task:
            response = self.client.v2[self.host_1, "actions", allowed_action, "run"].post(
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        job = JobLog.objects.filter(task=run_task.target_task).first()

        response = self.client.v2[job, "terminate"].post(data={})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "JOB_TERMINATION_ERROR",
                "desc": f"Can't terminate job #{job.id}, pid: 0 with status created",
                "level": "error",
            },
        )

    def test_adcm_4856_action_with_non_existing_component_fail(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        with RunTaskMock() as run_task:
            response = self.client.v2[self.host_1, "actions", allowed_action, "run"].post(
                data={
                    "hostComponentMap": [{"hostId": self.host_1.pk, "componentId": 1000}],
                    "config": {},
                    "adcmMeta": {},
                    "isVerbose": False,
                },
            )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertDictEqual(response.json(), {"detail": "Components with ids 1000 do not exist"})
        self.assertIsNone(run_task.target_task)

    def test_adcm_4856_action_with_non_existing_host_fail(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        with RunTaskMock() as run_task:
            response = self.client.v2[self.host_1, "actions", allowed_action, "run"].post(
                data={
                    "hostComponentMap": [{"hostId": 1000, "componentId": self.component_1.pk}],
                    "config": {},
                    "adcmMeta": {},
                    "isVerbose": False,
                },
            )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertDictEqual(response.json(), {"detail": "Hosts with ids 1000 do not exist"})
        self.assertIsNone(run_task.target_task)

    def test_adcm_4856_action_with_duplicated_hc_success(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        with RunTaskMock() as run_task:
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
        run_task.runner.run(run_task.target_task.pk)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")

    def test_adcm_4856_action_with_several_entries_hc_success(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        with RunTaskMock() as run_task:
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
        run_task.runner.run(run_task.target_task.pk)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")

    def test_adcm_5348_action_not_allowed_on_any_cluster_failed(self):
        test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        test_user = self.create_user(**test_user_credentials)

        child_role_action = Role.objects.get(name="Cluster Action: action")
        child_role_clusters = Role.objects.get(name="View cluster configurations")
        cluster_as_cluster_one = self.add_cluster(bundle=self.bundle_1, name="cluster_as_cluster_1")

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


class TestActionWithJinjaConfig(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        cluster_bundle = self.add_bundle(self.test_bundles_dir / "cluster_actions_jinja")
        self.cluster = self.add_cluster(cluster_bundle, "Cluster with Jinja Actions")
        self.service_1 = self.add_services_to_cluster(service_names=["first_service"], cluster=self.cluster).get()
        self.component_1: Component = Component.objects.get(service=self.service_1, prototype__name="first_component")

    def test_group_jinja_config(self):
        cluster_bundle = self.add_bundle(self.test_bundles_dir / "cluster_action_with_group_jinja")
        cluster = self.add_cluster(cluster_bundle, "Cluster with Jinja Actions 2")

        hosts = [self.add_host(provider=self.provider, fqdn=f"host-{i}", cluster=cluster) for i in range(1, 15)]

        service = self.add_services_to_cluster(service_names=["service_name"], cluster=cluster)[0]

        component = service.components.get(prototype__name="server")
        self.set_hostcomponent(
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

    def test_retrieve_jinja_config_old_processing(self):
        with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=False) as patched:
            self._test_retrieve_jinja_config()

        patched.assert_called()

    def test_retrieve_jinja_config_new_processing(self):
        with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=True) as patched:
            self._test_retrieve_jinja_config()

        patched.assert_called()

    def _test_retrieve_jinja_config(self):
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

    def test_adcm_6013_jinja_config_with_min_max_old_processing(self):
        with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=False) as patched:
            self._test_adcm_6013_jinja_config_with_min_max()

        patched.assert_called()

    def test_adcm_6013_jinja_config_with_min_max_new_processing(self):
        with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=True) as patched:
            self._test_adcm_6013_jinja_config_with_min_max()

        patched.assert_called()

    def _test_adcm_6013_jinja_config_with_min_max(self):
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

    def test_adcm_4703_action_retrieve_returns_500_old_processing(self):
        with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=False) as patched:
            self._test_adcm_4703_action_retrieve_returns_500()

        patched.assert_called()

    def test_adcm_4703_action_retrieve_returns_500_new_processing(self):
        with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=True) as patched:
            self._test_adcm_4703_action_retrieve_returns_500()

        patched.assert_called()

    def _test_adcm_4703_action_retrieve_returns_500(self) -> None:
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


class TestAction(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.action_with_config = Action.objects.filter(name="with_config", prototype=self.cluster_1.prototype).first()

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

        with RunTaskMock() as task_launch:
            response = self.client.v2[self.cluster_1, "actions", action, "run"].post(data={"shouldBlockObject": False})

        self.assertEqual(response.status_code, HTTP_200_OK)

        task_launch.target_task.refresh_from_db()
        self.assertIsNone(task_launch.target_task.lock)

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

            with RunTaskMock():
                response = self.client.v2[self.cluster_1, "actions", self.action_with_config, "run"].post(
                    data={"configuration": {"config": configuration["config"], "adcmMeta": configuration["adcmMeta"]}}
                )

            self.assertEqual(response.status_code, HTTP_200_OK)

            self.assertEqual(self.cluster_1.concerns.count(), 2)
            self.assertEqual(self.cluster_1.concerns.filter(type=ConcernType.FLAG).count(), 1)
            self.assertEqual(self.cluster_1.concerns.filter(type=ConcernType.LOCK).count(), 1)
