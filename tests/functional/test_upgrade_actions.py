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
Test "scripts" section of bundle's "upgrade" section
"""

# pylint: disable=no-self-use

import os
from typing import Set

import allure
import pytest
from coreapi.exceptions import ErrorMessage
from adcm_client.objects import Cluster, ADCMClient, Bundle
from adcm_pytest_plugin.utils import get_data_dir, catch_failed, parametrize_by_data_subdirs

from tests.library.assertions import sets_are_equal
from tests.library.errorcodes import INVALID_UPGRADE_DEFINITION, INVALID_OBJECT_DEFINITION


@parametrize_by_data_subdirs(__file__, 'validation', 'valid')
def test_validation_succeed_on_upload(sdk_client_fs, path):
    """Test that valid bundles with upgrade actions succeed to upload"""
    verbose_bundle_name = os.path.basename(path).replace('_', ' ').capitalize()
    with allure.step(f'Upload bundle "{verbose_bundle_name}" and expect it to succeed'), catch_failed(
        ErrorMessage, f'Bundle "{verbose_bundle_name}" should be uploaded successfully'
    ):
        bundle = sdk_client_fs.upload_from_fs(path)
        bundle.delete()


@pytest.mark.parametrize(
    ('bundle_dir_name', 'expected_error'),
    [
        ('bundle_switch_in_regular_actions', INVALID_OBJECT_DEFINITION),
        ('incorrect_internal_action', INVALID_UPGRADE_DEFINITION),
        ('no_bundle_switch', INVALID_UPGRADE_DEFINITION),
    ],
)
def test_validation_failed_on_upload(bundle_dir_name, expected_error, sdk_client_fs):
    """Test that invalid bundles with upgrade actions fails to upload"""
    verbose_bundle_name = bundle_dir_name.replace('_', ' ').capitalize()
    invalid_bundle_file = get_data_dir(__file__, 'validation', 'invalid', bundle_dir_name)
    with allure.step(f'Upload bundle "{verbose_bundle_name}" and expect upload to fail'):
        with pytest.raises(ErrorMessage) as e:
            sdk_client_fs.upload_from_fs(invalid_bundle_file)
        expected_error.equal(e)


class TestFailedUpgradeAction:
    """Test cases when upgrade action is failed during execution"""

    FAILURES_DIR = 'upgrade_failures'

    @pytest.fixture()
    def old_cluster(self, sdk_client_fs) -> Cluster:
        """Upload old cluster bundle and then create one"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, self.FAILURES_DIR, 'old'))
        return bundle.cluster_create('Test Cluster for Upgrade')

    def test_fail_before_switch(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails before bundle_switch was performed
        """
        expected_state = old_cluster.state
        expected_prototype_id = old_cluster.prototype_id
        self._upload_new_version(sdk_client_fs, 'before_switch')
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_prototype(old_cluster, expected_prototype_id)

    def test_fail_after_switch_with_on_fail(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails after bundle_switch was performed.
        Failed job has "on_fail" directive.
        """
        expected_state = 'something_is_wrong'
        restore_action_name = 'restore'
        bundle = self._upload_new_version(sdk_client_fs, 'after_switch_with_on_fail')
        expected_prototype_id = bundle.cluster_prototype().id
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_prototype(old_cluster, expected_prototype_id)
        self._check_action_list(old_cluster, {restore_action_name})

    def test_fail_after_switch_without_on_fail(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails after bundle_switch was performed.
        Failed job doesn't have "on_fail" directive.
        """
        expected_state = old_cluster.state
        bundle = self._upload_new_version(sdk_client_fs, 'after_switch')
        expected_prototype_id = bundle.cluster_prototype().id
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_prototype(old_cluster, expected_prototype_id)
        self._check_action_list(old_cluster, {})

    @allure.step('Upload new version of cluster bundle')
    def _upload_new_version(self, client: ADCMClient, name: str) -> Bundle:
        """Upload new version of bundle based on the given bundle file_name"""
        return client.upload_from_fs(get_data_dir(__file__, self.FAILURES_DIR, name))

    @allure.step('Upgrade cluster and expect it to enter the "{state}" state')
    def _upgrade_and_expect_state(self, cluster: Cluster, state: str):
        """Upgrade cluster to a new version and check if it's state is correct"""
        task = cluster.upgrade().do()
        assert task.wait() == 'failed', 'Upgrade action should has failed'
        cluster.reread()
        assert (
            actual_state := cluster.state
        ) == state, f'State after failed upgrade should be {state}, not {actual_state}'

    @allure.step('Check that cluster prototype is equal to {expected_prototype_id}')
    def _check_prototype(self, cluster: Cluster, expected_prototype_id: int):
        """Check that prototype of a cluster is the same as expected"""
        cluster.reread()
        assert (
            actual_id := cluster.prototype_id
        ) == expected_prototype_id, f'Prototype of cluster should be {expected_prototype_id}, not {actual_id}'

    @allure.step('Check list of available actions on cluster')
    def _check_action_list(self, cluster: Cluster, action_names: Set[str]):
        """Check that action list is equal to given one (by names)"""
        cluster.reread()
        presented_action_names = {a.name for a in cluster.action_list()}
        sets_are_equal(presented_action_names, action_names, message='Incorrect action list')
