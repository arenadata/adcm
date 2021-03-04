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
from typing import Union

import allure
import pytest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import Cluster, Provider, Host
from adcm_pytest_plugin.steps.actions import run_host_action_and_assert_result, \
    run_cluster_action_and_assert_result
from adcm_pytest_plugin.utils import get_data_dir


@allure.title("Create cluster")
@pytest.fixture()
def cluster(sdk_client_fs) -> Cluster:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    return bundle.cluster_prototype().cluster_create(name="Some cluster")


@allure.title("Create provider")
@pytest.fixture()
def provider(sdk_client_fs) -> Provider:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
    return bundle.provider_prototype().provider_create("Some provider")


class TestClusterActionsOnHost:

    @pytest.mark.parametrize("action_name", ["action_on_host", "action_on_host_multijob"])
    def test_availability(self, cluster: Cluster, provider: Provider, action_name):
        """
        Test that cluster host action is available on cluster host and is absent on cluster
        """
        host1 = provider.host_create("host_in_cluster")
        host2 = provider.host_create("host_not_in_cluster")
        cluster.host_add(host1)
        action_in_object_is_present(action_name, host1)
        action_in_object_is_absent(action_name, host2)
        action_in_object_is_absent(action_name, cluster)
        run_host_action_and_assert_result(host1, action_name, status="success")

    def test_availability_at_state(self, cluster: Cluster, provider: Provider):
        """
        Test that cluster host action is available on specify cluster state
        """
        action_name = "action_on_host_state_installed"
        host = provider.host_create("host_in_cluster")
        cluster.host_add(host)
        action_in_object_is_absent(action_name, host)
        run_cluster_action_and_assert_result(cluster, "switch_cluster_state")
        action_in_object_is_present(action_name, host)
        run_host_action_and_assert_result(host, action_name)

    def test_availability_at_host_state(self, cluster: Cluster, provider: Provider):
        """
        Test that cluster host action isn't available on specify host state
        """
        action_name = "action_on_host_state_installed"
        host = provider.host_create("host_in_cluster")
        cluster.host_add(host)
        action_in_object_is_absent(action_name, host)
        run_host_action_and_assert_result(host, "switch_host_state")
        action_in_object_is_absent(action_name, host)
        run_cluster_action_and_assert_result(cluster, "switch_cluster_state")
        action_in_object_is_present(action_name, host)
        run_host_action_and_assert_result(host, action_name)


def action_in_object_is_present(action: str, obj: Union[Cluster, Host]):
    with allure.step(f"Assert that action {action} is present in {_get_object_represent(obj)}"):
        try:
            obj.action(name=action)
        except ObjectNotFound as err:
            raise AssertionError(f"Action {action} not found in object {obj}") from err


def action_in_object_is_absent(action: str, obj: Union[Cluster, Host]):
    with allure.step(f"Assert that action {action} is absent in {_get_object_represent(obj)}"):
        with pytest.raises(ObjectNotFound):
            obj.action(name=action)


def _get_object_represent(obj: Union[Cluster, Host]) -> str:
    return f"host {obj.fqdn}" if isinstance(obj, Host) else f"cluster {obj.name}"
