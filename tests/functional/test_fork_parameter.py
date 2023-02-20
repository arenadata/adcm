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

"""Tests for ansible fork count param"""

# pylint: disable=redefined-outer-name
import allure
import pytest
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result
from adcm_pytest_plugin.utils import get_data_dir
from coreapi.exceptions import ErrorMessage

pytestmark = allure.link(url="https://arenadata.atlassian.net/browse/ADCM-1540", name="Test cases")


@pytest.fixture()
def testing_cluster(sdk_client_fs):
    """
    Prepared cluster for test
    """
    cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster")
    return cluster_bundle.cluster_prototype().cluster_create("Fork testing cluster")


def test_default_ansible_forks(testing_cluster):
    """
    Check that default ansible fork count is 5
    """
    run_cluster_action_and_assert_result(testing_cluster, "assert_fork", config={"fork_count": 5})
    run_cluster_action_and_assert_result(testing_cluster, "assert_fork_multijob", config={"fork_count": 5})


def test_custom_ansible_forks(sdk_client_fs, testing_cluster):
    """
    Check that custom ansible fork count works fine for job and multijob actions
    """
    custom_forks_count = 10
    sdk_client_fs.adcm().config_set_diff({"ansible_settings": {"forks": custom_forks_count}})
    run_cluster_action_and_assert_result(testing_cluster, "assert_fork", config={"fork_count": custom_forks_count})
    run_cluster_action_and_assert_result(
        testing_cluster,
        "assert_fork_multijob",
        config={"fork_count": custom_forks_count},
    )


@pytest.mark.parametrize("forks_count", [0, 101], ids=["0 forks", "101 fork"])
def test_negate_values(sdk_client_fs, forks_count):
    """
    Check that incorrect fork values is unacceptable
    """
    with pytest.raises(ErrorMessage, match="CONFIG_VALUE_ERROR"):
        sdk_client_fs.adcm().config_set_diff({"ansible_settings": {"forks": forks_count}})
