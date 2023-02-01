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

"""Tests for adcm_client capability"""

import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.plugin import parametrized_by_adcm_version
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_host_action_and_assert_result,
    run_service_action_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir


def old_adcm_images():
    """Prepare a list of old ADCM images"""
    return parametrized_by_adcm_version(adcm_min_version="2019.10.08")[0]


@pytest.mark.parametrize("image", old_adcm_images(), ids=repr, indirect=True)
def test_actions(sdk_client_fs: ADCMClient):
    """
    Tests that action works on latest adcm client and old adcm versions
    """
    cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'provider'))
    cluster = cluster_bundle.cluster_prototype().cluster_create(name="Some cluster")
    service = cluster.service_add(name="dummy")
    provider = provider_bundle.provider_create("provider_with_actions")
    host = provider.host_create(fqdn="localhost")
    run_cluster_action_and_assert_result(cluster, "dummy")
    run_service_action_and_assert_result(service, "dummy")
    run_host_action_and_assert_result(host, "dummy")
    assert provider.action(name="dummy").run().wait() == "success"
