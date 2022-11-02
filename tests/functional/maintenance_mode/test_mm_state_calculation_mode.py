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
Test designed to check MM state calculation logic for services/components
"""

import allure

from tests.functional.conftest import only_clean_adcm
from tests.functional.maintenance_mode.conftest import (
    ANOTHER_SERVICE_NAME,
    DEFAULT_SERVICE_NAME,
    MM_IS_OFF,
    MM_IS_ON,
    add_hosts_to_cluster,
    check_mm_is,
    set_maintenance_mode,
)


# pylint: disable=redefined-outer-name


@only_clean_adcm
def test_mm_state_service(api_client, cluster_with_mm, hosts):
    """Test to check maintenance_mode on services and hosts"""
    first_host, second_host, *_ = hosts
    first_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    second_service = cluster_with_mm.service_add(name=ANOTHER_SERVICE_NAME)
    first_component = first_service.component(name='first_component')
    second_component = first_service.component(name='second_component')

    add_hosts_to_cluster(cluster_with_mm, (first_host, second_host))
    cluster_with_mm.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
    )

    with allure.step('Check MM state calculation logic for service'):
        set_maintenance_mode(api_client=api_client, adcm_object=second_service, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_OFF, first_host, second_host, first_component, second_component, first_service)

        set_maintenance_mode(api_client=api_client, adcm_object=first_service, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_OFF, first_host, second_host)

        set_maintenance_mode(api_client=api_client, adcm_object=first_service, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=second_service, maintenance_mode=MM_IS_OFF)
        check_mm_is(
            MM_IS_OFF, first_host, second_host, first_component, second_component, first_service, second_service
        )


@only_clean_adcm
def test_mm_state_component(api_client, cluster_with_mm, hosts):
    """Test to check maintenance_mode on components and hosts"""
    first_host, second_host, *_ = hosts
    first_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    first_component = first_service.component(name='first_component')
    second_component = first_service.component(name='second_component')

    add_hosts_to_cluster(cluster_with_mm, (first_host, second_host))
    cluster_with_mm.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
    )

    with allure.step('Check MM state calculation logic for components'):
        set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_OFF, first_host, second_host, second_component, first_service)

        set_maintenance_mode(api_client=api_client, adcm_object=second_component, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_OFF, first_host, second_host)

        set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=second_component, maintenance_mode=MM_IS_OFF)
        check_mm_is(MM_IS_OFF, first_host, second_host, first_component, second_component, first_service)


@only_clean_adcm
def test_mm_state_host(api_client, cluster_with_mm, hosts):
    """Test to check maintenance_mode on components and hosts"""
    first_host, second_host, *_ = hosts
    first_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    first_component = first_service.component(name='first_component')
    second_component = first_service.component(name='second_component')

    add_hosts_to_cluster(cluster_with_mm, (first_host, second_host))
    cluster_with_mm.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
    )

    with allure.step('Check MM state calculation logic for hosts'):
        set_maintenance_mode(api_client=api_client, adcm_object=first_host, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_OFF, first_service, second_host, second_component)

        set_maintenance_mode(api_client=api_client, adcm_object=second_host, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_service, first_host, first_component, second_host, second_component)

        set_maintenance_mode(api_client=api_client, adcm_object=first_host, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=second_host, maintenance_mode=MM_IS_OFF)
        check_mm_is(MM_IS_OFF, first_service, first_host, first_component, second_host, second_component)
