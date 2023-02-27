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

"""Test designed to check valid values for getting MM: ON, OFF, CHANGING"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Component, Service

from tests.functional.maintenance_mode.conftest import (
    ANOTHER_SERVICE_NAME,
    BUNDLES_DIR,
    DEFAULT_SERVICE_NAME,
    FIRST_COMPONENT,
    MM_IS_CHANGING,
    MM_IS_OFF,
    MM_IS_ON,
    SECOND_COMPONENT,
    check_mm_is,
)
from tests.library.api.client import APIClient

# pylint: disable=redefined-outer-name


@pytest.fixture()
def cluster_with_mm(sdk_client_fs: ADCMClient) -> Cluster:
    """
    Upload cluster bundle with allowed MM,
    create and return cluster with default service
    """
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster_mm_action")
    cluster = bundle.cluster_create("Actions Cluster")
    cluster.service_add(name=DEFAULT_SERVICE_NAME)
    return cluster


def test_state_calculation_mode_service(api_client, cluster_with_mm, hosts):
    """Test to check CHANGING mode for service when object changes his maintenance mode"""
    first_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    second_service = cluster_with_mm.service_add(name=ANOTHER_SERVICE_NAME)
    first_component = first_service.component(name=FIRST_COMPONENT)
    second_component = first_service.component(name=SECOND_COMPONENT)

    cluster_with_mm.hostcomponent_set(
        (cluster_with_mm.host_add(hosts[0]), first_component),
        (cluster_with_mm.host_add(hosts[1]), second_component),
        (cluster_with_mm.host_add(hosts[2]), second_service.component()),
    )

    check_mm_is(MM_IS_OFF, first_service, second_service, first_component, second_component)
    with allure.step("Check service action maintenance mode set maintenance mode to CHANGING value"):
        _status_changing(api_client, second_service, MM_IS_ON)
        check_mm_is(MM_IS_CHANGING, second_service)
        check_mm_is(MM_IS_OFF, first_service, first_component, second_component)

    with allure.step("Check CHANGING mode on service does not change other objects on service"):
        _status_changing(api_client, first_service, MM_IS_ON)
        check_mm_is(MM_IS_CHANGING, first_service, second_service)
        check_mm_is(MM_IS_OFF, first_component, second_component)


def test_state_calculation_mode_component(api_client, cluster_with_mm, hosts):
    """Test to check CHANGING mode for component when object changes his maintenance mode"""
    first_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    second_service = cluster_with_mm.service_add(name=ANOTHER_SERVICE_NAME)
    first_component = first_service.component(name=FIRST_COMPONENT)
    second_component = first_service.component(name=SECOND_COMPONENT)

    cluster_with_mm.hostcomponent_set(
        (cluster_with_mm.host_add(hosts[0]), first_component),
        (cluster_with_mm.host_add(hosts[1]), second_component),
    )

    check_mm_is(MM_IS_OFF, first_service, second_service, first_component, second_component)
    with allure.step("Check component action maintenance mode set maintenance mode to CHANGING value"):
        _status_changing(api_client, first_component, MM_IS_ON)
        check_mm_is(MM_IS_CHANGING, first_component)
        check_mm_is(MM_IS_OFF, first_service, second_service, second_component)

    with allure.step("Check CHANGING mode on component does not change other objects in cluster"):
        _status_changing(api_client, second_component, MM_IS_ON)
        check_mm_is(MM_IS_CHANGING, first_component, second_component)
        check_mm_is(MM_IS_OFF, first_service, second_service)


def _status_changing(api_client: APIClient, adcm_object: Service | Component, maintenance_mode: str) -> None:
    """Try to change maintenance mode on ADCM objects and catch mode CHANGING"""
    client = api_client.service if isinstance(adcm_object, Service) else api_client.component
    client.change_maintenance_mode(adcm_object.id, maintenance_mode).check_code(200)
    adcm_object.reread()
