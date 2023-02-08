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

"""Tests for service delete method"""

# pylint: disable=redefined-outer-name

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Provider
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_host_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_service_action_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir

pytestmark = allure.link(url="https://arenadata.atlassian.net/browse/ADCM-2580", name="Test cases")

DEFAULT_ANSIBLE_VER = {"major": 2, "minor": 8}
ANSIBLE_9 = {"major": 2, "minor": 9}


def _prepare_cluster(client: ADCMClient, name):
    """
    Prepared cluster for test: create cluster, couple services and couple components.
    """
    cluster_bundle = client.upload_from_fs(get_data_dir(__file__) + "/cluster_" + name)
    cluster = cluster_bundle.cluster_prototype().cluster_create(name.replace("_", " "))
    cluster.service_add(name=name)
    return cluster


def _prepare_provider(client: ADCMClient, name):
    """
    Prepared provider for test: create provider, couple host.
    """
    bundle = client.upload_from_fs(get_data_dir(__file__) + "/provider_" + name)
    provider = bundle.provider_prototype().provider_create(name)
    provider.host_create(fqdn=name.replace("_", "-"))
    return provider


@pytest.fixture()
def cluster_no_venv(sdk_client_ms):
    """
    Prepared cluster for test: create cluster, couple services and couple components.
    """
    return _prepare_cluster(sdk_client_ms, "no_venv")


@pytest.fixture()
def cluster_obj_venv_default(sdk_client_ms):
    """
    Prepared cluster for test: create cluster, couple services and couple components.
    """
    return _prepare_cluster(sdk_client_ms, "obj_venv_default")


@pytest.fixture()
def provider_no_venv(sdk_client_ms):
    """
    Prepared provider for test: create provider, couple host.
    """
    return _prepare_provider(sdk_client_ms, "no_venv")


@pytest.fixture()
def provider_obj_venv_default(sdk_client_ms):
    """
    Prepared provider for test: create provider, couple host.
    """
    return _prepare_provider(sdk_client_ms, "obj_venv_default")


def test_default_ansible(
    cluster_no_venv: Cluster,
    cluster_obj_venv_default: Cluster,
    provider_no_venv: Provider,
    provider_obj_venv_default: Provider,
):
    """
    Check that by default (if developer write nothing) we have Ansible 2.8.
    """
    run_cluster_action_and_assert_result(cluster_no_venv, "no_venv", config=DEFAULT_ANSIBLE_VER)
    run_service_action_and_assert_result(cluster_no_venv.service(name="no_venv"), "no_venv", config=DEFAULT_ANSIBLE_VER)
    run_component_action_and_assert_result(
        cluster_no_venv.service(name="no_venv").component(name="no_venv"),
        "no_venv",
        config=DEFAULT_ANSIBLE_VER,
    )

    run_cluster_action_and_assert_result(cluster_obj_venv_default, "obj_venv_default", config=DEFAULT_ANSIBLE_VER)
    run_service_action_and_assert_result(
        cluster_obj_venv_default.service(name="obj_venv_default"),
        "obj_venv_default",
        config=DEFAULT_ANSIBLE_VER,
    )
    run_component_action_and_assert_result(
        cluster_obj_venv_default.service(name="obj_venv_default").component(name="obj_venv_default"),
        "obj_venv_default",
        config=DEFAULT_ANSIBLE_VER,
    )

    run_provider_action_and_assert_result(provider_no_venv, "no_venv", config=DEFAULT_ANSIBLE_VER)
    run_host_action_and_assert_result(provider_no_venv.host(fqdn="no-venv"), "no_venv", config=DEFAULT_ANSIBLE_VER)

    run_provider_action_and_assert_result(provider_obj_venv_default, "obj_venv_default", config=DEFAULT_ANSIBLE_VER)
    run_host_action_and_assert_result(
        provider_obj_venv_default.host(fqdn="obj-venv-default"),
        "obj_venv_default",
        config=DEFAULT_ANSIBLE_VER,
    )


@pytest.fixture()
def cluster_obj_venv_9(sdk_client_ms):
    """
    Prepared cluster for test: create cluster, couple services and couple components.
    """
    return _prepare_cluster(sdk_client_ms, "obj_venv_9")


@pytest.fixture()
def provider_obj_venv_9(sdk_client_ms):
    """
    Prepared provider for test: create provider, couple host.
    """
    return _prepare_provider(sdk_client_ms, "obj_venv_9")


def test_ansible_set_on_prototype(cluster_obj_venv_9: Cluster, provider_obj_venv_9: Provider):
    """
    Check that we able to change ansible on prototype level, by tweaking venv
    property for object.
    """
    run_cluster_action_and_assert_result(cluster_obj_venv_9, "obj_venv_9", config=ANSIBLE_9)
    run_service_action_and_assert_result(cluster_obj_venv_9.service(name="obj_venv_9"), "obj_venv_9", config=ANSIBLE_9)
    run_component_action_and_assert_result(
        cluster_obj_venv_9.service(name="obj_venv_9").component(name="obj_venv_9"),
        "obj_venv_9",
        config=ANSIBLE_9,
    )

    run_provider_action_and_assert_result(provider_obj_venv_9, "obj_venv_9", config=ANSIBLE_9)
    run_host_action_and_assert_result(provider_obj_venv_9.host(fqdn="obj-venv-9"), "obj_venv_9", config=ANSIBLE_9)


@pytest.fixture()
def cluster_obj_venv_default_action_9(sdk_client_ms):
    """
    Prepared cluster for test: create cluster, couple services and couple components.
    """
    return _prepare_cluster(sdk_client_ms, "obj_venv_default_action_9")


@pytest.fixture()
def cluster_obj_no_venv_action_9(sdk_client_ms):
    """
    Prepared cluster for test: create cluster, couple services and couple components.
    """
    return _prepare_cluster(sdk_client_ms, "obj_no_venv_action_9")


@pytest.fixture()
def provider_no_venv_action_9(sdk_client_ms):
    """
    Prepared provider for test: create provider, couple host.
    """
    return _prepare_provider(sdk_client_ms, "no_venv_action_9")


@pytest.fixture()
def provider_obj_venv_default_action_9(sdk_client_ms):
    """
    Prepared provider for test: create provider, couple host.
    """
    return _prepare_provider(sdk_client_ms, "obj_venv_default_action_9")


def test_ansible_set_on_action(
    cluster_obj_venv_default_action_9: Cluster,
    cluster_obj_no_venv_action_9: Cluster,
    provider_obj_venv_default_action_9: Provider,
    provider_no_venv_action_9: Provider,
):
    """
    Check that we able to change ansible on action.
    """
    run_cluster_action_and_assert_result(
        cluster_obj_venv_default_action_9, "obj_venv_default_action_9", config=ANSIBLE_9
    )
    run_service_action_and_assert_result(
        cluster_obj_venv_default_action_9.service(name="obj_venv_default_action_9"),
        "obj_venv_default_action_9",
        config=ANSIBLE_9,
    )
    run_component_action_and_assert_result(
        cluster_obj_venv_default_action_9.service(name="obj_venv_default_action_9").component(
            name="obj_venv_default_action_9"
        ),
        "obj_venv_default_action_9",
        config=ANSIBLE_9,
    )

    run_cluster_action_and_assert_result(cluster_obj_no_venv_action_9, "obj_no_venv_action_9", config=ANSIBLE_9)
    run_service_action_and_assert_result(
        cluster_obj_no_venv_action_9.service(name="obj_no_venv_action_9"),
        "obj_no_venv_action_9",
        config=ANSIBLE_9,
    )
    run_component_action_and_assert_result(
        cluster_obj_no_venv_action_9.service(name="obj_no_venv_action_9").component(name="obj_no_venv_action_9"),
        "obj_no_venv_action_9",
        config=ANSIBLE_9,
    )

    run_provider_action_and_assert_result(provider_no_venv_action_9, "no_venv_action_9", config=ANSIBLE_9)
    run_host_action_and_assert_result(
        provider_no_venv_action_9.host(fqdn="no-venv-action-9"),
        "no_venv_action_9",
        config=ANSIBLE_9,
    )

    run_provider_action_and_assert_result(
        provider_obj_venv_default_action_9, "obj_venv_default_action_9", config=ANSIBLE_9
    )
    run_host_action_and_assert_result(
        provider_obj_venv_default_action_9.host(fqdn="obj-venv-default-action-9"),
        "obj_venv_default_action_9",
        config=ANSIBLE_9,
    )
