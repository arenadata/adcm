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

"""Tests that known bugs aren't present anymore"""

import allure
import pytest
from adcm_client.objects import Cluster, Provider, Bundle
from adcm_pytest_plugin.utils import get_data_dir

from tests.functional.conftest import only_clean_adcm

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm, pytest.mark.regression]


def _cluster_bundle(sdk_client_fs) -> Bundle:
    """Get dummy cluster"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'dummy', 'cluster'))


def _provider_bundle(sdk_client_fs) -> Bundle:
    """Get dummy provider"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'dummy', 'provider'))


@pytest.fixture()
def cluster(sdk_client_fs) -> Cluster:
    """Get dummy cluster"""
    return _cluster_bundle(sdk_client_fs).cluster_create(name='Test Dummy Cluster')


@pytest.fixture()
def provider(sdk_client_fs) -> Provider:
    """Get dummy provider"""
    return _provider_bundle(sdk_client_fs).provider_create(name='Test Dummy Provider')


@allure.issue(url='https://arenadata.atlassian.net/browse/ADCM-2659')
def test_database_is_locked_during_upload(sdk_client_fs, provider):
    """
    Test that known bug that occurs during bundle upload when actions are running is not presented anymore
    """
    with allure.step('Create a lot of hosts and run a lot of actions on them'):
        for i in range(200):
            provider.host_create(f'host-{i}').action(name='dummy').run()
    with allure.step('Try to upload cluster bundle'):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'simple_cluster_from_dirty_upgrade'))
