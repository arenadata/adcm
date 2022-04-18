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
conftest.py for maintenance mode related tests
"""

# pylint: disable=redefined-outer-name

import os
from pathlib import Path
from typing import Tuple, Literal

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Provider, Host

BUNDLES_DIR = Path(os.path.dirname(__file__)) / 'bundles'

MM_IS_ON = 'on'
MM_IS_OFF = 'off'
MM_IS_DISABLED = 'disabled'

MaintenanceModeOnHostValue = Literal['on', 'off', 'disabled']

PROVIDER_NAME = 'Test Default Provider'
CLUSTER_WITH_MM_NAME = 'Test Cluster WITH Maintenance Mode'
CLUSTER_WITHOUT_MM_NAME = 'Test Cluster WITHOUT Maintenance Mode'
DEFAULT_SERVICE_NAME = 'test_service'
ANOTHER_SERVICE_NAME = 'another_service'


@pytest.fixture()
def provider(sdk_client_fs: ADCMClient) -> Provider:
    """Upload bundle and create default provider"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'default_provider')
    return bundle.provider_create(PROVIDER_NAME)


@pytest.fixture()
def hosts(provider) -> Tuple[Host, Host, Host, Host, Host, Host]:
    """Create 6 hosts from the default bundle"""
    return tuple(provider.host_create(f'test-host-{i}') for i in range(6))


@pytest.fixture()
def cluster_with_mm(sdk_client_fs: ADCMClient) -> Cluster:
    """
    Upload cluster bundle with allowed MM,
    create and return cluster with default service
    """
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'cluster_mm_allowed')
    cluster = bundle.cluster_create(CLUSTER_WITH_MM_NAME)
    cluster.service_add(name=DEFAULT_SERVICE_NAME)
    return cluster


@pytest.fixture()
def cluster_without_mm(sdk_client_fs: ADCMClient):
    """
    Upload cluster bundle with disallowed MM,
    create and return cluster with default service
    """
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'cluster_mm_disallowed')
    cluster = bundle.cluster_create(CLUSTER_WITHOUT_MM_NAME)
    cluster.service_add(name=DEFAULT_SERVICE_NAME)
    return cluster


def turn_mm_on(host: Host):
    """Turn maintenance mode "on" on host"""
    with allure.step(f'Turn MM "on" on host {host.fqdn}'):
        host.maintenance_mode = MM_IS_ON


def turn_mm_off(host: Host):
    """Turn maintenance mode "off" on host"""
    with allure.step(f'Turn MM "off" on host {host.fqdn}'):
        host.maintenance_mode = MM_IS_OFF
