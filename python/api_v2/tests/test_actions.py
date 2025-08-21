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
from pathlib import Path
from typing import Any, TypeAlias
from unittest.mock import patch
from uuid import uuid4
import json
import unittest

from cm.converters import orm_object_to_core_type
from cm.models import (
    ADCM,
    Action,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    ConcernType,
    Host,
    HostComponent,
    JobLog,
    MaintenanceMode,
    Process,
    ProcessStep,
    ProcessStepInput,
    Provider,
    Service,
    TaskLog,
)
from cm.services.jinja_env import _get_action_info
from cm.services.job.run.repo import ActionRepoImpl
from cm.services.wizard.schema_validation import ProcessOperationType, SubmitStepPayload
from cm.services.wizard.types import ProcessState, ProcessStepState
from cm.tests.mocks.task_runner import RunTaskMock
from django.contrib.contenttypes.models import ContentType
from jinja2 import Template
from rbac.models import Role
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
import yaml

from api_v2.tests.base import BaseAPITestCase

ObjectWithActions: TypeAlias = Cluster | Service | Component | Provider | Host


def render_template(file: Path, context: dict) -> Any:
    data = Template(source=file.read_text(encoding="utf-8")).render(**context)
    return yaml.safe_load(data)


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
        self.assertDictEqual(
            response.json(), {"code": "API_ERROR", "desc": "Components with ids 1000 do not exist", "level": "ERROR"}
        )
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
        self.assertDictEqual(
            response.json(), {"code": "API_ERROR", "desc": "Hosts with ids 1000 do not exist", "level": "ERROR"}
        )
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
        # ADCM-6746
        # with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=False) as patched:
        self._test_retrieve_jinja_config()

        # patched.assert_called()

    @unittest.skip("ADCM-6747")
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
        # ADCM-6746
        # with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=False) as patched:
        self._test_adcm_6013_jinja_config_with_min_max()

        # patched.assert_called()

    @unittest.skip("ADCM-6747")
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
        # ADCM-6746
        # with patch("cm.services.config.jinja.use_new_bundle_parsing_approach", return_value=False) as patched:
        self._test_adcm_4703_action_retrieve_returns_500()

        # patched.assert_called()

    @unittest.skip("ADCM-6747")
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


class TestWizard(BaseAPITestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        wizard_cluster_bundle = self.test_bundles_dir / "wizard_action"
        self.bundle_1 = self.add_bundle(source_dir=wizard_cluster_bundle)
        self.cluster_1 = self.add_cluster(bundle=self.bundle_1, name="cluster_1", description="cluster_1")

        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster_1).first()
        self.component_1 = Component.objects.filter(service=self.service_1).first()

        self.cluster_wizard_action = self.get_object_wizard_action(self.cluster_1)

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def _fill_wizard_steps_for_process(self, process_id: int, test_spec, previous_step_names) -> None:
        # Fill previous steps' `step_spec`, create inputs for them
        for step in ProcessStep.objects.filter(process_id=process_id, name__in=previous_step_names):
            step.step_spec = test_spec
            step.state = ProcessStepState.COMPLETED
            step.save(update_fields=["step_spec", "state"])
            ProcessStepInput.objects.create(step_id=step.id, job=None, configuration=test_spec)

    def test_create_process_success(self):
        self.assertEqual(Process.objects.count(), 0)
        self.assertEqual(ProcessStep.objects.count(), 0)

        self.client.login(**self.test_user_credentials)

        with self.subTest("No view permissions"):
            response = self.client.v2[
                self.cluster_1, "actions", self.get_object_wizard_action(self.cluster_1).pk, "processes"
            ].post(data={})
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("No run permissions"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
                response = self.client.v2[
                    self.cluster_1, "actions", self.get_object_wizard_action(self.cluster_1).pk, "processes"
                ].post(data={})
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.client.login(username="admin", password="admin")

        with self.subTest("All permissions"):
            for obj in (self.cluster_1, self.service_1, self.component_1):
                with self.subTest(f"create process for {obj}"):
                    response = self.client.v2[obj, "actions", self.get_object_wizard_action(obj).pk, "processes"].post(
                        data={}
                    )

                    self.assertEqual(response.status_code, HTTP_201_CREATED)
                    self.assertEqual(
                        Process.objects.filter(
                            object_id=obj.pk, object_type=orm_object_to_core_type(obj).value
                        ).count(),
                        1,
                    )

                    process = Process.objects.get(object_id=obj.pk, object_type=orm_object_to_core_type(obj).value)

                    flags = ConcernItem.objects.filter(
                        owner_id=self.cluster_1.pk,
                        owner_type=ContentType.objects.get_for_model(model=Cluster),
                        cause=ConcernCause.CONFIGURING_PROCESS,
                    )
                    self.assertEqual(flags.count(), 1)

                    self.assertEqual(ProcessStep.objects.filter(process=process).count(), 6)

                    expected_response_template = self.test_files_dir / "responses" / "wizard" / "create_process.yml"
                    _step_ids = {f"{name}_id": id_ for name, id_ in process.steps.values_list("name", "id")}
                    expected_response = render_template(
                        file=expected_response_template,
                        context={
                            "process_id": process.id,
                            "created_at": process.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                            **_step_ids,
                        },
                    )

                    response = response.json()

                    self.assertDictContainsSubset(expected_response, response)

    def test_retrieve_config_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        target_step = ProcessStep.objects.get(process_id=process.id, name="stage1_step1", display_name="Stage1.Step1")

        for obj in (self.cluster_1, self.service_1, self.component_1):
            with self.subTest(f"retrieve process for {obj}"):
                response = self.client.v2[
                    obj,
                    "actions",
                    self.get_object_wizard_action(obj).pk,
                    "processes",
                    process.id,
                    "steps",
                    target_step.pk,
                ].get()
                self.assertEqual(response.status_code, HTTP_200_OK)

                target_step.refresh_from_db()
                expected_spec = [
                    {"name": "integer_field", "type": "integer", "default": 2},
                    {"name": "string_field", "type": "string", "default": "string_value"},
                ]
                self.assertListEqual(target_step.step_spec, expected_spec)

                response_template = self.test_files_dir / "responses" / "wizard" / "retrieve_config_step.yml"
                expected_response = render_template(file=response_template, context={"step_id": target_step.id})
                self.assertDictEqual(response.json(), expected_response)

    def test_retrieve_operation_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        target_step = ProcessStep.objects.get(process_id=process.id, name="stage2_step2", display_name="Stage2.Step2")

        for obj in (self.cluster_1, self.service_1, self.component_1):
            with self.subTest(f"retrieve operation for {obj}"):
                obj.state = "new_state"
                obj.save(update_fields=["state"])

                response = self.client.v2[
                    obj,
                    "actions",
                    self.get_object_wizard_action(obj).pk,
                    "processes",
                    process.id,
                    "steps",
                    target_step.pk,
                ].get()
                self.assertEqual(response.status_code, HTTP_200_OK)

                target_step.refresh_from_db()
                expected_spec = [
                    {
                        "display_name": "Sleep",
                        "name": "sleep_script",
                        "params": {"test_params": ["new_state"]},
                        "script": "scripts/sleep.yaml",
                        "script_type": "ansible",
                    }
                ]
                self.assertListEqual(target_step.step_spec, expected_spec)

                response_template = self.test_files_dir / "responses" / "wizard" / "retrieve_operation_step.yml"
                expected_response = render_template(file=response_template, context={"step_id": target_step.id})
                self.assertDictEqual(response.json(), expected_response)

    def test_retrieve_wizard_action_success(self):
        with self.subTest("not a wizard action"):
            response = self.client.v2[
                "adcm", "actions", Action.objects.filter(prototype=ADCM.objects.first().prototype).first().pk
            ].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIsNone(response.json()["processes"], None)

        for obj in (self.cluster_1, self.service_1, self.component_1):
            with self.subTest(f"wizard action of {obj} without processes"):
                response = self.client.v2[obj, "actions", self.get_object_wizard_action(obj).pk].get()
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertListEqual(response.json()["processes"], [])

        for obj in (self.cluster_1, self.service_1, self.component_1):
            with self.subTest(f"wizard action of {obj} with process"):
                process = self.get_process(self.start_process(obj))

                self._fill_wizard_steps_for_process(process.id, {"test": "spec"}, {"stage1_step1", "stage2_step1"})

                response = self.client.v2[obj, "actions", self.get_object_wizard_action(obj).pk].get()
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(len(response.json()["processes"]), 1)
                self.assertEqual(response.json()["processes"][0]["syncKey"], str(process.sync_key))

    def test_submit_operation_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        initial_sync_key = process.sync_key
        test_spec, previous_step_names = {"test": "spec"}, {"stage1_step1", "stage2_step1"}

        target_operation_step = ProcessStep.objects.get(
            process_id=process.id, name="stage2_step2", display_name="Stage2.Step2"
        )

        self._fill_wizard_steps_for_process(process.id, test_spec, previous_step_names)

        # render step
        response = self.client.v2[
            self.cluster_1,
            "actions",
            self.cluster_wizard_action.pk,
            "processes",
            process.id,
            "steps",
            target_operation_step.id,
        ].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.assertFalse(ProcessStepInput.objects.filter(step_id=target_operation_step.id).exists())
        self.assertFalse(TaskLog.objects.filter(action=self.cluster_wizard_action).exists())

        # submit step
        response = self.client.v2[
            self.cluster_1, "actions", self.cluster_wizard_action.pk, "processes", process.id, "operation"
        ].post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {"step_id": target_operation_step.id, "process_sync_key": process.sync_key},
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], process.id)
        self.assertEqual(response.json()["createdAt"], str(process.created_at.isoformat().replace("+00:00", "Z")))
        self.assertEqual(sum(len(stage["steps"]) for stage in response.json()["stages"]), process.steps.count())

        target_operation_step.refresh_from_db()
        expected_spec = [
            {
                "display_name": "Sleep",
                "name": "sleep_script",
                "params": {"test_params": ["created"]},
                "script": "scripts/sleep.yaml",
                "script_type": "ansible",
            }
        ]
        self.assertListEqual(target_operation_step.step_spec, expected_spec)

        task = TaskLog.objects.get(action=self.cluster_wizard_action)
        input_ = ProcessStepInput.objects.get(step_id=target_operation_step.id)

        self.assertIsNone(input_.configuration)
        self.assertEqual(input_.job_id, task.id)

        process.refresh_from_db()
        self.assertNotEqual(initial_sync_key, process.sync_key)

        # check that previous steps and inputs are not affected
        for step in ProcessStep.objects.filter(process_id=process.id, name__in=previous_step_names):
            self.assertDictEqual(step.step_spec, test_spec)
            input_ = ProcessStepInput.objects.get(step_id=step.id)
            self.assertDictEqual(input_.configuration, test_spec)
            self.assertIsNone(input_.job)

    def test_submit_config_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        self.assertIsNone(process.last_completed_step_id)

        process_sync_key_initial = process.sync_key
        target_config_step = ProcessStep.objects.get(
            process_id=process.id, name="stage2_step1", display_name="Stage2.Step1"
        )
        self.assertEqual(target_config_step.state, ProcessStepState.CREATED)

        # fill `step_spec` with test data, create ProcessStepInputs
        test_step_spec = {"test": "data"}
        test_config = {"test": "config"}
        steps_qs = ProcessStep.objects.filter(process_id=process.id)
        steps_qs.update(step_spec=test_step_spec)
        for step_id in steps_qs.values_list("id", flat=True):
            ProcessStepInput.objects.create(step_id=step_id, configuration=test_config, job=None)

        # make all previous steps 'completed'
        ProcessStep.objects.filter(id__lt=target_config_step.id).update(state=ProcessStepState.COMPLETED)

        new_config = {"config": {"new": "config"}, "adcm_meta": {}}
        response = self.client.v2[
            self.cluster_1, "actions", self.cluster_wizard_action.pk, "processes", process.id, "operation"
        ].post(
            data={
                "method": ProcessOperationType.SUBMIT,
                "params": {
                    "configuration": new_config,
                    "step_id": target_config_step.id,
                    "process_sync_key": process.sync_key,
                },
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        # check that all next steps' specs are None and there is not ProcessStepInput for them
        steps_qs = ProcessStep.objects.filter(process_id=process.id)
        expected_step_specs = {
            ("stage1_step1", "Stage1.Step1"): test_step_spec,
            ("stage2_step1", "Stage2.Step1"): test_step_spec,
            ("stage2_step2", "Stage2.Step2"): None,
            ("stage3_step1", "Stage3.Step1"): None,
            ("stage4_step1", "Stage4.Step1"): None,
            ("stage4_step2", "Stage4.Step2"): None,
        }
        actual_step_specs = {
            (name, display_name): spec
            for name, display_name, spec in steps_qs.values_list("name", "display_name", "step_spec")
        }
        self.assertDictEqual(actual_step_specs, expected_step_specs)

        expected_steps_with_inputs: set[int] = set(
            steps_qs.exclude(name__in=["stage2_step2", "stage3_step1", "stage4_step1", "stage4_step2"]).values_list(
                "id", flat=True
            )
        )
        actual_steps_with_inputs = set(
            ProcessStepInput.objects.filter(step_id__in=steps_qs.values_list("id", flat=True)).values_list(
                "step_id", flat=True
            )
        )
        self.assertSetEqual(expected_steps_with_inputs, actual_steps_with_inputs)

        # check inputs' config and job
        input_config = {"attr": new_config.pop("adcm_meta"), **new_config}
        for input_ in ProcessStepInput.objects.filter(step_id__in=steps_qs.values_list("id", flat=True)):
            expected_config = input_config if input_.step_id == target_config_step.id else test_config
            self.assertDictEqual(input_.configuration, expected_config)
            self.assertIsNone(input_.job)

        # check that process's sync_key is updated
        process.refresh_from_db()
        self.assertNotEqual(process_sync_key_initial, process.sync_key)
        self.assertEqual(process.last_completed_step_id, target_config_step.id)

        target_config_step.refresh_from_db()
        self.assertEqual(target_config_step.state, ProcessStepState.COMPLETED)

    def test_submit_step_config_called_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        process_sync_key = str(process.sync_key)
        step_id = process.steps.first().pk
        config = {"config": {"a": "b", "c": {}}, "adcmMeta": {"/a": {"isActive": True}}}
        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process / "operation"

        self.assertEqual(process.state, ProcessState.CREATED)

        with patch("api_v2.generic.wizard.views.perform_operation") as perform_operation_mock:
            payload = {
                "method": "submit",
                "params": {"processSyncKey": process_sync_key, "stepId": step_id, "configuration": config},
            }
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_200_OK)

        expected_action = ActionRepoImpl.get_action(process.action.pk)
        expected_payload = SubmitStepPayload.model_validate(
            {
                "method": "submit",
                "params": {
                    "process_sync_key": process_sync_key,
                    "step_id": step_id,
                    "configuration": {"config": {"a": "b", "c": {}}, "adcm_meta": {"/a": {"isActive": True}}},
                },
            }
        )
        perform_operation_mock.assert_called_once_with(
            process_id=process.id, payload=expected_payload, object_=self.cluster_1, action=expected_action
        )

    def test_submit_step_job_called_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        process_sync_key = str(process.sync_key)
        step_id = process.steps.get(name="stage2_step2").pk
        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process / "operation"

        self.assertEqual(process.state, ProcessState.CREATED)

        # make all previous steps 'completed'
        ProcessStep.objects.filter(id__lt=step_id).update(state=ProcessStepState.COMPLETED)

        with patch("api_v2.generic.wizard.views.perform_operation") as perform_operation_mock:
            payload = {
                "method": "submit",
                "params": {"processSyncKey": process_sync_key, "stepId": step_id},
            }
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_200_OK)

        expected_action = ActionRepoImpl.get_action(process.action.pk)
        expected_payload = SubmitStepPayload.model_validate(
            {**payload, "params": {"process_sync_key": process_sync_key, "step_id": step_id}}
        )
        perform_operation_mock.assert_called_once_with(
            process_id=process.id, payload=expected_payload, object_=self.cluster_1, action=expected_action
        )

    def test_reset_operation_step_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        all_steps = ["stage1_step1", "stage2_step1", "stage2_step2", "stage3_step1", "stage4_step1", "stage4_step2"]
        test_spec, previous_step_names = {"test": "spec"}, ["stage1_step1", "stage2_step1"]
        new_config = {"config": {"new": "config"}, "adcm_meta": {}}

        self._fill_wizard_steps_for_process(process.id, test_spec, previous_step_names)

        for step_name in all_steps:
            target_step = ProcessStep.objects.get(process_id=process.id, name=step_name)
            submit_params = {
                "method": ProcessOperationType.SUBMIT,
                "params": {"step_id": target_step.id, "process_sync_key": process.sync_key},
            }
            if step_name in ["stage1_step1", "stage2_step1"]:
                submit_params["params"]["configuration"] = new_config
            else:
                target_step.state = ProcessStepState.COMPLETED
                target_step.save(update_fields=["state"])

        target_step_to_reset = ProcessStep.objects.get(process_id=process.id, name="stage3_step1")

        response = self.client.v2[
            self.cluster_1, "actions", self.cluster_wizard_action.pk, "processes", process.id, "operation"
        ].post(
            data={
                "method": ProcessOperationType.RESET,
                "params": {"step_id": target_step_to_reset.id, "process_sync_key": process.sync_key},
            }
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        previous_step_to_target = ProcessStep.objects.get(process_id=process.id, name="stage2_step2")
        previous_step_with_input = ProcessStep.objects.get(process_id=process.id, name="stage2_step1")

        self.assertEqual(previous_step_to_target.state, ProcessStepState.COMPLETED)

        self.assertIsNotNone(previous_step_with_input.processstepinput)
        self.assertIsNotNone(previous_step_with_input.step_spec)

        for step_name in all_steps[3:]:
            step = ProcessStep.objects.get(process_id=process.id, name=step_name)
            self.assertEqual(step.state, ProcessStepState.CREATED)
            self.assertFalse(hasattr(step, "processstepinput"))
            self.assertIsNone(step.step_spec)

    def test_complete_process_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        process_sync_key = process.sync_key
        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process / "operation"

        self.assertEqual(process.state, ProcessState.CREATED)

        payload = {"method": "complete", "params": {"processSyncKey": process_sync_key}}
        response = endpoint.post(data=payload)
        self.assertEqual(response.status_code, HTTP_200_OK)
        process.refresh_from_db()
        self.assertEqual(process.state, ProcessState.COMPLETED)

        flags = ConcernItem.objects.filter(
            owner_id=self.cluster_1.pk,
            owner_type=ContentType.objects.get_for_model(model=Cluster),
            cause=ConcernCause.CONFIGURING_PROCESS,
        )
        self.assertEqual(flags.count(), 0)

    def test_retrieve_process_success(self):
        process = self.get_process(self.start_process(self.cluster_1))
        self.assertEqual(process.state, ProcessState.CREATED)

        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process
        with self.subTest("All permissions"):
            response = endpoint.get()
            self.assertEqual(response.status_code, HTTP_200_OK)

        with self.subTest("No view permissions"):
            self.client.login(**self.test_user_credentials)
            response = endpoint.get()
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("No run permissions"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
                response = endpoint.get()
                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_operation_validation_fail(self):
        process = self.get_process(self.start_process(self.cluster_1))
        endpoint = self.get_endpoint_to_processes(self.cluster_1) / process / "operation"

        with self.subTest("Incorrect method"):
            payload = {"method": "notexist", "params": {"process_sync_key": process.sync_key}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            error = response.json()["desc"]
            self.assertIn(
                "Input tag 'notexist' found using 'method' does not match any of the expected tags",
                error,
            )

        with self.subTest("Incorrect payload for complete"):
            payload = {"method": "complete", "params": {}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            error = response.json()["desc"]
            self.assertIn("params.process_sync_key", error)
            self.assertIn("Field required [type=missing, input_value={}, input_type=dict]", error)

        with self.subTest("Incorrect payload for submit: missing stepId"):
            payload = {"method": "submit", "params": {"processSyncKey": process.sync_key}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            error = response.json()["desc"]
            self.assertIn("step_id", error)
            self.assertIn("Field required [type=missing", error)  # TODO: not informative description (3 errors)

        with self.subTest("Incorrect payload for complete: wrong sync key"):
            payload = {"method": "complete", "params": {"processSyncKey": uuid4()}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            error = response.json()["desc"]
            self.assertIn("Sync key mismatch", error)

        with self.subTest("Incorrect payload for complete: wrong sync key type"):
            payload = {"method": "complete", "params": {"processSyncKey": "abs"}}
            response = endpoint.post(data=payload)
            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            error = response.json()["desc"]
            self.assertIn("Input should be a valid UUID", error)

    def start_process(self, obj: Cluster | Service | Component):
        endpoint = self.get_endpoint_to_processes(obj)
        response = endpoint.post(data={})
        return response.json()["id"]

    def get_endpoint_to_processes(self, obj: Cluster | Service | Component):
        return self.client.v2[obj, "actions", self.get_object_wizard_action(obj).pk, "processes"]

    def get_process(self, process_id: int) -> Process:
        return Process.objects.get(pk=process_id)

    def get_object_wizard_action(self, obj: Cluster | Service | Component) -> Action:
        return Action.objects.get(name="wizard_jinja", prototype=obj.prototype)
