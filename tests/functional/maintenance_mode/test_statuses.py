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
Test statuses aggregation when hosts are in MM
"""

from operator import not_, truth
from typing import Collection, Tuple

import allure
import pytest
import requests
from adcm_client.objects import ADCMClient, Cluster, Component
from tests.functional.conftest import only_clean_adcm
from tests.functional.maintenance_mode.conftest import (
    ANOTHER_SERVICE_NAME,
    DEFAULT_SERVICE_NAME,
    FIRST_COMPONENT,
    MM_IS_OFF,
    MM_IS_ON,
    SECOND_COMPONENT,
    add_hosts_to_cluster,
    set_maintenance_mode,
    turn_mm_on,
)
from tests.library.assertions import dicts_are_equal
from tests.library.status import ADCMObjectStatusChanger

# pylint: disable=redefined-outer-name

CHILDREN_KEY = "chilren"

POSITIVE_STATUS = 0
NEGATIVE_STATUS = 16


pytestmark = [only_clean_adcm]


@pytest.fixture()
def status_changer(sdk_client_fs, adcm_fs) -> ADCMObjectStatusChanger:
    """Init status changer"""
    return ADCMObjectStatusChanger(sdk_client_fs, adcm_fs)


@pytest.fixture()
def deployed_component(cluster_with_mm, hosts) -> Tuple[Component, Component, Component, Component]:
    """Add components on 3 hosts"""
    default_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    another_service = cluster_with_mm.service_add(name=ANOTHER_SERVICE_NAME)
    default_component_1 = default_service.component(name=FIRST_COMPONENT)
    default_component_2 = default_service.component(name=SECOND_COMPONENT)
    another_component_1 = another_service.component(name=FIRST_COMPONENT)
    another_component_2 = another_service.component(name=SECOND_COMPONENT)
    host_1, host_2, host_3, *_ = hosts
    add_hosts_to_cluster(cluster_with_mm, (host_1, host_2, host_3))
    cluster_with_mm.hostcomponent_set(
        (host_1, default_component_1),
        (host_2, default_component_1),
        (host_2, default_component_2),
        (host_3, default_component_2),
        (host_3, another_component_1),
        (host_3, another_component_2),
    )
    return default_component_1, default_component_2, another_component_1, another_component_2


class TestStatusAggregationWithMM:
    """Test status aggregation with hosts in MM"""

    # pylint: disable-next=too-many-arguments
    def test_turn_mm_after_negative_status(
        self, api_client, status_changer, sdk_client_fs, cluster_with_mm, deployed_component, hosts
    ):
        """
        Test status aggregation when components on hosts are turned "off" after MM turned "on" on host
        """
        cluster = cluster_with_mm
        service = cluster.service(name=DEFAULT_SERVICE_NAME)
        component, *_ = deployed_component
        _, host_2, host_3, *_ = hosts

        service_name = service.name
        component_name = f"{service_name}.{component.name}"
        host_on_component_name = f"{component_name}.{host_2.fqdn}"

        self.enable_cluster(status_changer, cluster)

        with allure.step(f"Disable component {component_name} on host {host_2.fqdn} and host itself"):
            status_changer.set_host_negative_status(host_2)
            status_changer.set_component_negative_status((host_2, component))
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                cluster.name,
                {service.name},
                {component_name},
                {host_on_component_name},
                {host_2.fqdn},
            )

        turn_mm_on(api_client, host_2)

        with allure.step("Expect nothing but host and component on it to be disabled"):
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                components_on_hosts={host_on_component_name},
                hosts={host_2.fqdn},
            )

        self._turn_off_component_not_on_mm_host(sdk_client_fs, status_changer, cluster, host_2, host_3)

    # pylint: disable-next=too-many-arguments
    def test_turn_mm_before_negative_status(
        self, api_client, status_changer, sdk_client_fs, cluster_with_mm, deployed_component, hosts
    ):
        """
        Test status aggregation when components on hosts are turned "off" before MM turned "on" on host
        """
        _, host_2, host_3, *_ = hosts
        cluster = cluster_with_mm
        service = cluster.service(name=DEFAULT_SERVICE_NAME)
        component, *_ = deployed_component

        service_name = service.name
        component_name = f"{service_name}.{component.name}"
        host_on_component_name = f"{component_name}.{host_2.fqdn}"

        turn_mm_on(api_client, host_2)

        self.enable_cluster(status_changer, cluster)

        with allure.step(f"Disable component {component_name} on host {host_2.fqdn} and host itself"):
            status_changer.set_host_negative_status(host_2)
            status_changer.set_component_negative_status((host_2, component))
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                components_on_hosts={host_on_component_name},
                hosts={host_2.fqdn},
            )

        self._turn_off_component_not_on_mm_host(sdk_client_fs, status_changer, cluster, host_2, host_3)

    # pylint: disable=too-many-arguments
    def test_status_service_mm_changed(
        self, api_client, status_changer, sdk_client_fs, cluster_with_mm, deployed_component, hosts
    ):
        cluster = cluster_with_mm
        service = cluster.service(name=DEFAULT_SERVICE_NAME)
        component, *_ = deployed_component
        _, host_2, *_ = hosts

        service_name = service.name
        component_name = f"{service_name}.{component.name}"
        host_on_component_name = f"{component_name}.{host_2.fqdn}"

        self.enable_cluster(status_changer, cluster)

        with allure.step(f"Disable component {component_name} on host {host_2.fqdn}"):
            status_changer.set_component_negative_status((host_2, component))
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                cluster=cluster.name,
                services={service_name},
                components={component_name},
                components_on_hosts={host_on_component_name},
                hosts=(),
            )

        with allure.step("Turn MM 'ON' on service and check statuses"):
            set_maintenance_mode(api_client, service, MM_IS_ON)
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                cluster=None,
                services=(),
                components=(),
                components_on_hosts={host_on_component_name},
                hosts=(),
            )

        with allure.step("Turn MM 'OFF' on service and check statuses"):
            set_maintenance_mode(api_client, service, MM_IS_OFF)
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                cluster=cluster.name,
                services={service_name},
                components={component_name},
                components_on_hosts={host_on_component_name},
                hosts=(),
            )

    # pylint: disable=too-many-arguments,too-many-locals
    def test_status_component_mm_changed(
        self, api_client, status_changer, sdk_client_fs, cluster_with_mm, deployed_component, hosts
    ):
        cluster = cluster_with_mm
        service = cluster.service(name=DEFAULT_SERVICE_NAME)
        component_1, component_2, *_ = deployed_component
        _, host_2, *_ = hosts

        service_name = service.name
        component_name = f"{service_name}.{component_1.name}"
        host_on_component_name = f"{component_name}.{host_2.fqdn}"
        component_2_name = f"{service_name}.{component_2.name}"
        host_on_component_2_name = f"{component_2_name}.{host_2.fqdn}"

        self.enable_cluster(status_changer, cluster)

        with allure.step(f"Disable component {component_name} on host {host_2.fqdn}"):
            status_changer.set_component_negative_status((host_2, component_1))
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                cluster=cluster.name,
                services={service_name},
                components={component_name},
                components_on_hosts={host_on_component_name},
                hosts=(),
            )

        with allure.step("Turn 'ON' first component's MM and check statuses"):
            set_maintenance_mode(api_client, component_1, MM_IS_ON)
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                cluster=None,
                services=(),
                components=(),
                components_on_hosts={host_on_component_name},
                hosts=(),
            )

        with allure.step(f"Disable component {component_2_name} on host {host_2.fqdn}"):
            status_changer.set_component_negative_status((host_2, component_2))
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                cluster=cluster.name,
                services={service_name},
                components={component_2_name},
                components_on_hosts={host_on_component_name, host_on_component_2_name},
                hosts=(),
            )

        with allure.step("Turn MM 'ON' on second component and check statuses"):
            set_maintenance_mode(api_client, component_2, MM_IS_ON)
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                cluster=None,
                services=(),
                components=(),
                components_on_hosts={host_on_component_name, host_on_component_2_name},
                hosts=(),
            )

        with allure.step("Turn off MM on second component"):
            set_maintenance_mode(api_client, component_2, MM_IS_OFF)
            check_statuses(
                retrieve_status(sdk_client_fs, cluster),
                cluster.name,
                services={service_name},
                components={component_2_name},
                components_on_hosts={host_on_component_name, host_on_component_2_name},
                hosts=(),
            )

    @allure.step('Turn all components in cluster "on"')
    def enable_cluster(self, status_changer, cluster) -> None:
        """Enable all components on all hosts of the cluster"""
        status_changer.enable_cluster(cluster)

    # pylint: disable-next=too-many-arguments
    def _turn_off_component_not_on_mm_host(self, client, status_changer, cluster, host_2, host_3):
        service = cluster.service(name=DEFAULT_SERVICE_NAME)
        component_1 = service.component(name=FIRST_COMPONENT)
        component_2 = service.component(name=SECOND_COMPONENT)
        service_name = service.name
        component_name = f"{service_name}.{component_1.name}"
        host_on_component_name = f"{component_name}.{host_2.fqdn}"

        with allure.step(
            f'Turn "off" component "{component_2.name}" on host {host_3.fqdn} '
            "and expect it to affect aggregation statuses"
        ):
            status_changer.set_component_negative_status((host_3, component_2))
            check_statuses(
                retrieve_status(client, cluster),
                cluster=cluster.name,
                services={service_name},
                components={f"{service_name}.{component_2.name}"},
                components_on_hosts={host_on_component_name, f"{service_name}.{component_2.name}.{host_3.fqdn}"},
                hosts={host_2.fqdn},
            )


def retrieve_status(client: ADCMClient, cluster: Cluster) -> dict:
    """Get status map for cluster"""
    url = f"{client.url}/api/v1/cluster/{cluster.id}/status/?view=interface"
    response = requests.get(url, headers={"Authorization": f"Token {client.api_token()}"})
    data = response.json()
    return {
        "name": data["name"],
        "status": data["status"],
        "hosts": {host["name"]: {"status": host["status"]} for host in data[CHILDREN_KEY]["hosts"]},
        "services": {
            service["name"]: {
                "status": service["status"],
                "components": {
                    hc["name"]: {
                        "status": hc["status"],
                        "hosts": {host_info["name"]: {"status": host_info["status"]} for host_info in hc["hosts"]},
                    }
                    for hc in service["hc"]
                },
            }
            for service in data[CHILDREN_KEY]["services"]
        },
    }


@allure.step("Check statuses of a cluster's objects")  # pylint: disable-next=too-many-arguments
def check_statuses(
    statuses: dict,
    cluster: str = None,
    services: Collection[str] = (),
    components: Collection[str] = (),
    components_on_hosts: Collection[str] = (),
    hosts: Collection[str] = (),
    default_positive: bool = True,
) -> None:
    """
    If `default_positive` is True then objects' names in arguments
    are expected to have negative status
    otherwise the positive status is expected
    """
    p = not_ if default_positive else truth

    expected_statuses = {
        "name": statuses["name"],
        "status": _expected_status(p(bool(cluster))),
        "hosts": {
            fqdn: {"status": _expected_status(p(fqdn in hosts))} for fqdn, host_dict in statuses["hosts"].items()
        },
        "services": {
            service_name: {
                "status": _expected_status(p(service_name in services)),
                "components": {
                    component_name: {
                        "status": _expected_status(p(f"{service_name}.{component_name}" in components)),
                        "hosts": {
                            fqdn: {
                                "status": _expected_status(
                                    p(f"{service_name}.{component_name}.{fqdn}" in components_on_hosts)
                                )
                            }
                            for fqdn, host_dict in component_dict["hosts"].items()
                        },
                    }
                    for component_name, component_dict in service_dict["components"].items()
                },
            }
            for service_name, service_dict in statuses["services"].items()
        },
    }

    dicts_are_equal(statuses, expected_statuses, "Status map isn't correct.\nCheck attachments for more details.")


def _expected_status(positive: bool = True) -> int:
    return POSITIVE_STATUS if positive else NEGATIVE_STATUS
