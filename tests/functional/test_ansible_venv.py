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

import allure
import pytest
from adcm_client.objects import Cluster
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result, run_service_action_and_assert_result, run_component_action_and_assert_result
from adcm_pytest_plugin.utils import get_data_dir

pytestmark = allure.link(url="https://arenadata.atlassian.net/browse/ADCM-1540", name="Test cases")

DEFAULT_DJANGO_VERSION_JOB_CONFIG = dict(major=2, minor=8)

@pytest.fixture()
def cluster_with_subobj(sdk_client_fs):
    """
    Prepared cluster for test: create cluster, couple services and couple components.
    """
    cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster_no_venv")
    return cluster_bundle.cluster_prototype().cluster_create("Fork testing cluster")


def test_default_ansible(cluster_with_subobj: Cluster):
    """
    Check that by default (if developer write nothing) we have Ansible 2.8.
    """
    run_cluster_action_and_assert_result(cluster_with_subobj, "no_venv", config=DEFAULT_DJANGO_VERSION_JOB_CONFIG)
    run_service_action_and_assert_result(cluster_with_subobj.service("no_venv"), "no_venv", config=DEFAULT_DJANGO_VERSION_JOB_CONFIG)
    run_service_action_and_assert_result(cluster_with_subobj.service("no_venv").component("no_venv"), "no_venv", config=DEFAULT_DJANGO_VERSION_JOB_CONFIG)


def test_ansible_set_on_prototype(cluster_with_subobj: Cluster):
    """
    Check that we able to change ansible on prototype level, by tweaking venv
    property for object.
    """
    run_cluster_action_and_assert_result(cluster_with_subobj, "obj_venv_9")
    run_service_action_and_assert_result(cluster_with_subobj.service("obj_venv_9"), "obj_venv_9")
    run_service_action_and_assert_result(cluster_with_subobj.service("obj_venv_9").component("obj_venv_9"), "obj_venv_9")

