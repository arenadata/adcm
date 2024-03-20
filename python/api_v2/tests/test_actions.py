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
import json

from cm.models import (
    Action,
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    HostProvider,
    JobLog,
    MaintenanceMode,
    ServiceComponent,
)
from cm.tests.mocks.task_runner import RunTaskMock
from django.urls import reverse
from rbac.models import Role
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from api_v2.tests.base import BaseAPITestCase

ObjectWithActions: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider | Host


def get_viewname_and_kwargs_for_object(object_: ObjectWithActions) -> tuple[str, dict[str, int]]:
    if isinstance(object_, ClusterObject):
        return "v2:service-action-list", {"service_pk": object_.pk, "cluster_pk": object_.cluster.pk}

    if isinstance(object_, ServiceComponent):
        return "v2:component-action-list", {
            "component_pk": object_.pk,
            "service_pk": object_.service.pk,
            "cluster_pk": object_.cluster.pk,
        }

    classname: str = object_.__class__.__name__.lower()
    # change hostp->p is for hostprovider->provider mutation for viewname
    return f"v2:{classname.replace('hostp', 'p')}-action-list", {f"{classname}_pk": object_.pk}


class TestActionsFiltering(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_bundle = self.add_bundle(self.test_bundles_dir / "cluster_actions")
        self.cluster = self.add_cluster(self.cluster_bundle, "Cluster with Actions")
        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster).get()
        self.component_1: ServiceComponent = ServiceComponent.objects.get(
            service=self.service_1, prototype__name="component_1"
        )
        self.component_2: ServiceComponent = ServiceComponent.objects.get(
            service=self.service_1, prototype__name="component_2"
        )
        self.add_services_to_cluster(service_names=["service_2"], cluster=self.cluster)

        provider_bundle = self.add_bundle(self.test_bundles_dir / "provider_actions")
        self.hostprovider = self.add_provider(provider_bundle, "Provider with Actions")
        self.host_1 = self.add_host(provider_bundle, self.hostprovider, "host-1")
        self.host_2 = self.add_host(provider_bundle, self.hostprovider, "host-2")

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

    def test_filter_object_own_actions_success(self) -> None:
        for object_ in (self.cluster, self.service_1, self.component_1, self.hostprovider, self.host_1):
            viewname, object_kwargs = get_viewname_and_kwargs_for_object(object_=object_)
            with self.subTest(msg=f"{object_.__class__.__name__} at different states"):
                self.check_object_action_list(
                    viewname=viewname, object_kwargs=object_kwargs, expected_actions=self.available_at_created_no_multi
                )

                object_.set_multi_state(self.flag_multi_state)

                self.check_object_action_list(
                    viewname=viewname, object_kwargs=object_kwargs, expected_actions=self.available_at_created_flag
                )

                object_.unset_multi_state(self.flag_multi_state)
                object_.set_multi_state(self.bag_multi_state)

                self.check_object_action_list(
                    viewname=viewname, object_kwargs=object_kwargs, expected_actions=self.available_at_created_bag
                )

                object_.unset_multi_state(self.bag_multi_state)
                object_.set_state(self.installed_state)

                self.check_object_action_list(
                    viewname=viewname,
                    object_kwargs=object_kwargs,
                    expected_actions=self.available_at_installed_no_multi,
                )

                object_.set_multi_state(self.flag_multi_state)

                self.check_object_action_list(
                    viewname=viewname, object_kwargs=object_kwargs, expected_actions=self.available_at_installed_flag
                )

                object_.unset_multi_state(self.flag_multi_state)
                object_.set_multi_state(self.bag_multi_state)

                self.check_object_action_list(
                    viewname=viewname, object_kwargs=object_kwargs, expected_actions=self.available_at_installed_bag
                )

    def test_filter_host_actions_success(self) -> None:
        check_host_1_actions = partial(
            self.check_object_action_list, *get_viewname_and_kwargs_for_object(object_=self.host_1)
        )
        check_host_2_actions = partial(
            self.check_object_action_list, *get_viewname_and_kwargs_for_object(object_=self.host_2)
        )
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

    def test_adcm_4516_disallowed_host_action_not_executable_success(self) -> None:
        self.add_host_to_cluster(self.cluster, self.host_1)
        disallowed_action = Action.objects.filter(display_name="cluster_host_action_disallowed").first()
        check_host_1_actions = partial(
            self.check_object_action_list, *get_viewname_and_kwargs_for_object(object_=self.host_1)
        )
        check_host_1_actions(
            expected_actions=[
                *self.available_at_created_no_multi,
                "from cluster any",
                "cluster_host_action_allowed",
                "cluster_host_action_disallowed",
            ]
        )

        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save(update_fields=["maintenance_mode"])

        with RunTaskMock() as run_task:
            response = self.client.post(
                path=reverse(
                    viewname="v2:host-action-run",
                    kwargs={"host_pk": self.host_1.pk, "pk": disallowed_action.pk},
                ),
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
            response = self.client.post(
                path=reverse(
                    viewname="v2:host-action-run",
                    kwargs={"host_pk": self.host_1.pk, "pk": allowed_action.pk},
                ),
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        job = JobLog.objects.filter(task=run_task.target_task).first()

        response = self.client.post(path=reverse(viewname="v2:joblog-terminate", kwargs={"pk": job.pk}), data={})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "JOB_TERMINATION_ERROR",
                "desc": "Can't terminate job #1, pid: 0 with status created",
                "level": "error",
            },
        )

    def test_adcm_4856_action_with_non_existing_component_fail(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        with RunTaskMock() as run_task:
            response = self.client.post(
                path=reverse(
                    viewname="v2:host-action-run",
                    kwargs={"host_pk": self.host_1.pk, "pk": allowed_action.pk},
                ),
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
            response = self.client.post(
                path=reverse(
                    viewname="v2:host-action-run",
                    kwargs={"host_pk": self.host_1.pk, "pk": allowed_action.pk},
                ),
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
            response = self.client.post(
                path=reverse(
                    viewname="v2:host-action-run",
                    kwargs={"host_pk": self.host_1.pk, "pk": allowed_action.pk},
                ),
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
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()

        with RunTaskMock() as run_task:
            response = self.client.post(
                path=reverse(
                    viewname="v2:host-action-run",
                    kwargs={"host_pk": self.host_1.pk, "pk": allowed_action.pk},
                ),
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

        response = self.client.get(
            path=reverse(viewname="v2:cluster-action-list", kwargs={"cluster_pk": cluster_as_cluster_one.pk})
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        self.client.login(**test_user_credentials)
        response = self.client.get(
            path=reverse(viewname="v2:cluster-action-list", kwargs={"cluster_pk": cluster_as_cluster_one.pk})
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def check_object_action_list(self, viewname: str, object_kwargs: dict, expected_actions: list[str]) -> None:
        response = self.client.get(path=reverse(viewname=viewname, kwargs=object_kwargs))

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
        self.component_1: ServiceComponent = ServiceComponent.objects.get(
            service=self.service_1, prototype__name="first_component"
        )

    def test_retrieve_jinja_config(self):
        action = Action.objects.filter(name="check_state", prototype=self.cluster.prototype).first()

        response = self.client.get(
            path=reverse(viewname="v2:cluster-action-detail", kwargs={"cluster_pk": self.cluster.pk, "pk": action.pk})
        )

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

    def test_adcm_4703_action_retrieve_returns_500(self) -> None:
        for object_ in (self.cluster, self.service_1, self.component_1):
            with self.subTest(object_.__class__.__name__):
                viewname, kwargs = get_viewname_and_kwargs_for_object(object_)
                response = self.client.get(path=reverse(viewname=viewname, kwargs=kwargs))
                self.assertEqual(response.status_code, HTTP_200_OK)

                for action_id in map(itemgetter("id"), response.json()):
                    response = self.client.get(
                        path=reverse(viewname=viewname.replace("-list", "-detail"), kwargs={**kwargs, "pk": action_id})
                    )
                    self.assertEqual(response.status_code, HTTP_200_OK)


class TestAction(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.action_with_config = Action.objects.filter(name="with_config", prototype=self.cluster_1.prototype).first()

    def test_retrieve_with_config(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:cluster-action-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.action_with_config.pk},
            )
        )

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
