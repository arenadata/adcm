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

# pylint: disable=redefined-outer-name

"""RBAC actions testing conftest.py"""

from pathlib import Path

import pytest
from adcm_client.objects import Bundle, Cluster, Provider
from adcm_pytest_plugin.utils import random_string

ALL_SERVICE_NAMES = (
    "actions_service",
    "config_changing_service",
    "only_component_actions",
    "only_service_actions",
    "no_components",
)

DATA_DIR = Path(__file__).parent / "bundles"


@pytest.fixture()
def actions_cluster_bundle(sdk_client_fs) -> Bundle:
    """Upload bundle of the cluster with "sophisticated" actions"""
    return sdk_client_fs.upload_from_fs(str(DATA_DIR / "cluster"))


@pytest.fixture()
def simple_cluster_bundle(sdk_client_fs) -> Bundle:
    """Upload bundle of the cluster with basic actions"""
    return sdk_client_fs.upload_from_fs(str(DATA_DIR / "clone_cluster"))


@pytest.fixture()
def actions_provider_bundle(sdk_client_fs) -> Bundle:
    """Upload bundle of the provider with "sophisticated" actions"""
    return sdk_client_fs.upload_from_fs(str(DATA_DIR / "provider"))


@pytest.fixture()
def simple_provider_bundle(sdk_client_fs) -> Bundle:
    """Upload bundle of the provider with basic actions"""
    return sdk_client_fs.upload_from_fs(str(DATA_DIR / "clone_provider"))


@pytest.fixture()
def actions_cluster(actions_cluster_bundle) -> Cluster:
    """Get Actions cluster with all services attached"""
    cluster = actions_cluster_bundle.cluster_create(name="Test Actions Cluster")
    for service_name in ALL_SERVICE_NAMES:
        cluster.service_add(name=service_name)
    return cluster


@pytest.fixture()
def simple_cluster(simple_cluster_bundle) -> Cluster:
    """Cluster based on simple cluster bundle"""
    cluster = simple_cluster_bundle.cluster_create(name="Test Simple Cluster")
    cluster.service_add(name="actions_service")
    return cluster


@pytest.fixture()
def actions_provider(actions_provider_bundle) -> Provider:
    """Provider based on actions provider bundle"""
    provider = actions_provider_bundle.provider_create(name="Test Actions Provider")
    provider.host_create(fqdn=f"test-actions-host-{random_string(8)}")
    return provider


@pytest.fixture()
def simple_provider(simple_provider_bundle) -> Provider:
    """Provider based on simple provider bundle"""
    provider = simple_provider_bundle.provider_create(name="Test Simple Provider")
    provider.host_create(fqdn=f"test-simple-host-{random_string(8)}")
    return provider
