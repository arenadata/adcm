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
import json
import os
from typing import Set

import allure
import pytest
from coreapi.exceptions import ErrorMessage
from adcm_client.objects import Cluster, ADCMClient, Bundle
from adcm_pytest_plugin.utils import get_data_dir, catch_failed, parametrize_by_data_subdirs, random_string
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result

from tests.library.assertions import sets_are_equal
from tests.library.errorcodes import INVALID_UPGRADE_DEFINITION, INVALID_OBJECT_DEFINITION


class TestUploadValidation:
    """Test cases when upload bundles"""

    @parametrize_by_data_subdirs(__file__, 'validation', 'valid')
    def test_validation_succeed_on_upload(self, sdk_client_fs, path):
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
    def test_validation_failed_on_upload(self, bundle_dir_name, expected_error, sdk_client_fs):
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
    TEST_SERVICE_NAME = 'test_service'

    @pytest.fixture()
    def old_cluster(self, sdk_client_fs) -> Cluster:
        """Upload old cluster bundle and then create one"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, self.FAILURES_DIR, 'old'))
        cluster = bundle.cluster_create('Test Cluster for Upgrade')
        cluster.service_add(name=self.TEST_SERVICE_NAME)
        return cluster

    def test_fail_before_switch(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails before bundle_switch was performed
        """
        old_bundle = old_cluster.bundle()
        expected_state = old_cluster.state
        expected_prototype_id = old_cluster.prototype_id

        self._upload_new_version(sdk_client_fs, 'before_switch')
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_prototype(old_cluster, expected_prototype_id)
        check_cluster_objects_configs_equal_bundle_default(old_cluster, old_bundle)

    def test_fail_after_switch_with_on_fail(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails after bundle_switch was performed.
        Failed job has "on_fail" directive.
        """
        restore_action_name = 'restore'
        expected_state = 'something_is_wrong'
        expected_state_after_restore = 'upgraded'

        bundle = self._upload_new_version(sdk_client_fs, 'after_switch_with_on_fail')
        expected_prototype_id = bundle.cluster_prototype().id
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_prototype(old_cluster, expected_prototype_id)
        check_cluster_objects_configs_equal_bundle_default(old_cluster, bundle)
        self._check_action_list(old_cluster, {restore_action_name})
        run_cluster_action_and_assert_result(old_cluster, restore_action_name)
        self._check_state(old_cluster, expected_state_after_restore)

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
        check_cluster_objects_configs_equal_bundle_default(old_cluster, bundle)
        self._check_action_list(old_cluster, {})

    @pytest.mark.parametrize(
        'upgrade_name',
        ['fail_after_bundle_switch', 'fail_before_bundle_switch'],
        ids=['fail_before_switch', 'fail_after_switch'],
    )
    def test_fail_with_both_action_states_set(self, upgrade_name: str, sdk_client_fs, old_cluster):
        """
        Test bundle action fails before/after bundle_switch
        when both on_success and on_fail are presented in action block
        """
        self._upload_new_version(sdk_client_fs, 'upgrade_action_has_on_fail')
        self._upgrade_and_expect_state(old_cluster, 'something_failed', name=upgrade_name)

    @allure.step('Upload new version of cluster bundle')
    def _upload_new_version(self, client: ADCMClient, name: str) -> Bundle:
        """Upload new version of bundle based on the given bundle file_name"""
        return client.upload_from_fs(get_data_dir(__file__, self.FAILURES_DIR, name))

    @allure.step('Upgrade cluster and expect it to enter the "{state}" state')
    def _upgrade_and_expect_state(self, cluster: Cluster, state: str, **kwargs):
        """
        Upgrade cluster to a new version (expect upgrade to fail)
        and check if it's state is correct
        """
        task = cluster.upgrade(**kwargs).do()
        assert task.wait() == 'failed', 'Upgrade action should have failed'
        self._check_state(cluster, state)

    @allure.step('Check cluster state is equal to "{state}"')
    def _check_state(self, cluster: Cluster, state: str):
        """Check state of a cluster"""
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


def check_cluster_objects_configs_equal_bundle_default(
    cluster: Cluster, bundle: Bundle, *, service_name: str = 'test_service'
):
    """
    Check that configurations of cluster, its services and components
    are equal to configurations of newly created cluster from given bundle
    """
    with allure.step(
        f'Check configuration of cluster {cluster.name} is equal to default configuration of cluster from {bundle.name}'
    ):
        actual_configs = _extract_configs(cluster)
        cluster_with_defaults = bundle.cluster_create(f'Cluster to take config from {random_string(4)}')
        cluster_with_defaults.service_add(name=service_name)
        expected_configs = _extract_configs(cluster_with_defaults)

        if actual_configs == expected_configs:
            return
        allure.attach(
            json.dumps(expected_configs, indent=2),
            name='Expected cluster objects configuration',
            attachment_type=allure.attachment_type.JSON,
        )
        allure.attach(
            json.dumps(actual_configs, indent=2),
            name='Actual cluster objects configuration',
            attachment_type=allure.attachment_type.JSON,
        )
        raise AssertionError("Cluster objects' configs aren't equal to expected, check attachments for more details")


def _extract_configs(cluster: Cluster):
    """Extract configurations of the cluster, its services and components as dict"""
    return {
        'config': dict(cluster.config()),
        'services': {
            service.name: {
                'config': dict(service.config()),
                'components': {
                    component.name: {'config': dict(component.config())} for component in service.component_list()
                },
            }
            for service in cluster.service_list()
        },
    }


class TestUpgradeActionRelations:
    """Test cases when upgrade action"""

    @pytest.mark.parametrize(
        ("folder_dir", "file_dir"),
        [
            ('upgrade_failures', 'before_switch'),
            ('upgrade_success', 'after_switch'),
        ],
    )
    def test_check_upgrade_actions_relations(self, sdk_client_fs, folder_dir, file_dir):
        """
        Test bundle action fails before bundle_switch was performed
        """

        jobs_before = sdk_client_fs.job_list()
        logs_before = [log for data in jobs_before for log in data.log_files]
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, folder_dir, 'old'))
        cluster = bundle.cluster_create('Test Cluster for Upgrade')
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, folder_dir, file_dir))
        with allure.step("Check cluster actions list before update"):
            actions_before = cluster.action_list()
            assert len(actions_before) == 1, "Should be 1 action"
            assert actions_before[0].display_name == "dummy_action", "Should be action 'dummy_action'"
        cluster.upgrade().do().wait()
        cluster.reread()
        with allure.step("Check jobs"):
            jobs = sdk_client_fs.job_list()
            jobs_expected = 3 + len(jobs_before)
            assert len(jobs) == jobs_expected, f"There are should be {jobs_expected} jobs"
            assert (
                len({'first action after switch', 'switch action', 'first_action'} & {j.display_name for j in jobs})
                == 3
            ), "Jobs names differ"
            logs_expected = 6 + len(logs_before)
            assert (
                len([log for data in jobs for log in data.log_files]) == logs_expected
            ), f"There are should be {logs_expected} or more log files"
        with allure.step("Check cluster actions list after update"):
            actions_after = cluster.action_list()
            assert len(actions_after) == 2 if "success" in folder_dir else 1, "Not all actions avaliable"
            assert {action.display_name for action in actions_after} == (
                {'dummy_action', 'restore'} if "success" in folder_dir else {'dummy_action'}
            ), "Not all actions avaliable"
