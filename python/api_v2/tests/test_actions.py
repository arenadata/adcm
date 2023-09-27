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
from typing import TypeAlias

from api_v2.tests.base import BaseAPITestCase
from cm.models import (
    Action,
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    ServiceComponent,
)
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_409_CONFLICT

ObjectWithActions: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider | Host


class TestActionsFiltering(BaseAPITestCase):  # pylint: disable=too-many-instance-attributes
    def setUp(self) -> None:
        super().setUp()

        cluster_bundle = self.add_bundle(self.test_bundles_dir / "cluster_actions")
        self.cluster = self.add_cluster(cluster_bundle, "Cluster with Actions")
        self.service_1 = self.add_service_to_cluster("service_1", self.cluster)
        self.component_1: ServiceComponent = ServiceComponent.objects.get(
            service=self.service_1, prototype__name="component_1"
        )
        self.add_service_to_cluster("service_2", self.cluster)

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
            viewname, object_kwargs = self.get_viewname_and_kwargs_for_object(object_=object_)
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
            self.check_object_action_list, *self.get_viewname_and_kwargs_for_object(object_=self.host_1)
        )
        check_host_2_actions = partial(
            self.check_object_action_list, *self.get_viewname_and_kwargs_for_object(object_=self.host_2)
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
        allowed_action = Action.objects.filter(display_name="cluster_host_action_allowed").first()
        disallowed_action = Action.objects.filter(display_name="cluster_host_action_disallowed").first()
        check_host_1_actions = partial(
            self.check_object_action_list, *self.get_viewname_and_kwargs_for_object(object_=self.host_1)
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

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-action-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": allowed_action.pk},
            ),
            data={"host_component_map": [], "config": {}, "attr": {}, "is_verbose": False},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-action-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": disallowed_action.pk},
            ),
            data={"host_component_map": [], "config": {}, "attr": {}, "is_verbose": False},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    @staticmethod
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

    def check_object_action_list(self, viewname: str, object_kwargs: dict, expected_actions: list[str]) -> None:
        response: Response = self.client.get(path=reverse(viewname=viewname, kwargs=object_kwargs))

        self.assertEqual(response.status_code, HTTP_200_OK)

        data = response.json()
        self.assertTrue(isinstance(data, list))
        self.assertTrue(all("displayName" in entry for entry in data))
        actual_actions = sorted(entry["displayName"] for entry in data)
        self.assertListEqual(actual_actions, sorted(expected_actions))
