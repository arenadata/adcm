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

"""
Test designed to check that actions are disallowed when cluster object in MM
"""

import allure
import pytest
from adcm_client.objects import Cluster
from tests.functional.maintenance_mode.conftest import (
    BUNDLES_DIR,
    MM_IS_OFF,
    MM_IS_ON,
    add_hosts_to_cluster,
    check_actions_availability,
    check_mm_is,
    set_maintenance_mode,
)

# pylint: disable=redefined-outer-name

CLUSTER_OBJECTS = ("cluster", "service", "component")


@pytest.fixture()
def cluster_mm_action_disallowed(sdk_client_fs) -> Cluster:
    """Upload and create cluster with service and component actions from cluster"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster_mm_actions_disallowed")
    cluster = bundle.cluster_create("Cluster with actions")
    cluster.service_add(name="first_service")
    return cluster


def test_mm_action(api_client, cluster_mm_action_disallowed, hosts):
    """
    Test to check actions for cluster objects are disallowed when object in MM
    """
    host_in_mm, regular_host, *_ = hosts
    cluster = cluster_mm_action_disallowed
    first_service = cluster.service()
    first_component = first_service.component(name="first_component")
    second_component = first_service.component(name="second_component")

    add_hosts_to_cluster(cluster, (host_in_mm, regular_host))
    cluster.hostcomponent_set((host_in_mm, first_component), (regular_host, second_component))

    with allure.step("Switch host MM to 'ON' and check enabled and disabled actions"):
        set_maintenance_mode(api_client, host_in_mm, MM_IS_ON)
        check_mm_is(MM_IS_ON, first_component, host_in_mm)

        expected_enabled = {f"{obj_type}_action_allowed" for obj_type in CLUSTER_OBJECTS if "component" in obj_type}
        expected_disabled = {f"{obj_type}_action_disallowed" for obj_type in CLUSTER_OBJECTS if "component" in obj_type}

        check_actions_availability(
            adcm_object=first_component, expected_enabled=expected_enabled, expected_disabled=expected_disabled
        )

    with allure.step(
        "Switch host MM to 'OFF', switch component with action to MM 'ON' and check enabled and disabled actions"
    ):
        set_maintenance_mode(api_client, host_in_mm, MM_IS_OFF)
        set_maintenance_mode(api_client, first_component, MM_IS_ON)
        check_mm_is(MM_IS_ON, first_component)

        expected_enabled = {f"{obj_type}_action_allowed" for obj_type in CLUSTER_OBJECTS if "component" in obj_type}
        expected_disabled = {f"{obj_type}_action_disallowed" for obj_type in CLUSTER_OBJECTS if "component" in obj_type}

        check_actions_availability(
            adcm_object=first_component, expected_enabled=expected_enabled, expected_disabled=expected_disabled
        )

    with allure.step("Switch component MM to 'OFF', switch service MM to 'ON' and check enabled and disabled actions"):
        set_maintenance_mode(api_client, first_component, MM_IS_OFF)
        set_maintenance_mode(api_client, first_service, MM_IS_ON)
        check_mm_is(MM_IS_ON, first_service, first_component, second_component)

        expected_enabled = {f"{obj_type}_action_allowed" for obj_type in CLUSTER_OBJECTS if "service" in obj_type}
        expected_disabled = {f"{obj_type}_action_disallowed" for obj_type in CLUSTER_OBJECTS if "service" in obj_type}

        check_actions_availability(
            adcm_object=first_service, expected_enabled=expected_enabled, expected_disabled=expected_disabled
        )
        check_actions_availability(
            adcm_object=first_service, expected_enabled=expected_enabled, expected_disabled=expected_disabled
        )
