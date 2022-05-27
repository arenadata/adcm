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

import json
import os
from typing import Set, Tuple

import allure
import pytest
from adcm_client.objects import Cluster, ADCMClient, Bundle, Host
from adcm_pytest_plugin.docker_utils import get_file_from_container, ADCM
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result
from adcm_pytest_plugin.utils import get_data_dir, catch_failed, parametrize_by_data_subdirs, random_string
from coreapi.exceptions import ErrorMessage

from tests.functional.conftest import only_clean_adcm
from tests.functional.tools import build_hc_for_hc_acl_action, get_inventory_file
from tests.library.assertions import sets_are_equal
from tests.library.errorcodes import INVALID_UPGRADE_DEFINITION, INVALID_OBJECT_DEFINITION, INVALID_ACTION_DEFINITION

# pylint: disable=redefined-outer-name, no-self-use

TEST_SERVICE_NAME = 'test_service'
FAILURES_DIR = 'upgrade_failures'
NEW_SERVICE = 'new_service'
SERVICE_WILL_BE_REMOVED = 'will_be_removed'

UPGRADE_EXTRA_ARGS = {'upgrade_with_config': {'config': {'parampampam': 'somestring'}}}


# !===== FUNCS =====!


create_cluster_from_old_bundle = pytest.mark.parametrize(
    'old_cluster', [('successful', 'old')], indirect=True, ids=['successful_old_bundle']
)


def _create_old_cluster(client, *dirs):
    bundle = client.upload_from_fs(get_data_dir(__file__, *dirs))
    cluster = bundle.cluster_create('Test Cluster for Upgrade')
    cluster.service_add(name=TEST_SERVICE_NAME)
    return cluster


@pytest.fixture()
def old_cluster(request, sdk_client_fs) -> Cluster:
    """Upload old cluster bundle and then create one"""
    return _create_old_cluster(sdk_client_fs, *request.param)


@pytest.fixture()
def two_hosts(sdk_client_fs, old_cluster) -> Tuple[Host, Host]:
    """Two hosts created and added to an old cluster"""
    provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'provider'))
    provider = provider_bundle.provider_create(name='Too Simple Provider')
    return old_cluster.host_add(provider.host_create('first-host')), old_cluster.host_add(
        provider.host_create('second-host')
    )


@allure.step('Check cluster state is equal to "{state}"')
def check_state(cluster: Cluster, state: str):
    """Check state of a cluster"""
    cluster.reread()
    assert (actual_state := cluster.state) == state, f'State after failed upgrade should be {state}, not {actual_state}'


@allure.step('Check that cluster prototype is equal to {expected_prototype_id}')
def check_prototype(cluster: Cluster, expected_prototype_id: int):
    """Check that prototype of a cluster is the same as expected"""
    cluster.reread()
    assert (
        actual_id := cluster.prototype_id
    ) == expected_prototype_id, f'Prototype of cluster should be {expected_prototype_id}, not {actual_id}'


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


def _compare_inventory_files(adcm_fs, job_id: int):
    """Compare two inventory files: one from local storage (expected) and one from docker container with ADCM"""
    inventory_file = get_file_from_container(adcm_fs, f'/adcm/data/run/{job_id}/', 'inventory.json')
    actual_inventory = json.loads(inventory_file.read().decode('utf-8'))
    with open(get_data_dir(__file__, 'successful', f'inventory_{job_id}.json'), 'rb') as file:
        expected_inventory = json.load(file)
    if actual_inventory == expected_inventory:
        return
    allure.attach(
        json.dumps(expected_inventory, indent=2),
        name=f'Expected inventory of job {job_id}',
        attachment_type=allure.attachment_type.JSON,
    )
    allure.attach(
        json.dumps(actual_inventory, indent=2),
        name=f'Actual inventory of job {job_id}',
        attachment_type=allure.attachment_type.JSON,
    )
    raise AssertionError(f'Inventories should be equal for job {job_id}.\nSee attachments for more details.')


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


@allure.step('Check service "{service_name}" is in cluster')
def _check_service_is_in_cluster(cluster: Cluster, service_name: str):
    assert service_name in [
        service.name for service in cluster.service_list()
    ], f'Service "{service_name}" is not presented in cluster "{cluster.name}"'


@allure.step('Check service "{service_name}" is not in cluster')
def _check_service_is_not_in_cluster(cluster: Cluster, service_name: str):
    assert service_name not in [
        service.name for service in cluster.service_list()
    ], f'Service "{service_name}" should not be presented in cluster "{cluster.name}"'


def _get_hc_names(hc_map) -> Set[Tuple[str, str, str]]:
    return set(map(lambda x: (x['host'], x['service_name'], x['component']), hc_map))


def _get_component_prototype_id(bundle, service_name, component_name) -> int:
    service_proto = bundle.service_prototype(name=service_name)
    component = next((c for c in service_proto.components if c['name'] == component_name), None)
    if component is None:
        raise ValueError(f'Component "{component_name}" is not presented in prototype of service "{service_name}"')
    return component['id']


def _set_hc_and_prepare_new_hc_for_upgrade_action(old_cluster, new_bundle, host_1, host_2):
    second_component_id = _get_component_prototype_id(new_bundle, TEST_SERVICE_NAME, 'second_component')
    some_component_id = _get_component_prototype_id(new_bundle, NEW_SERVICE, 'some_component')
    test_component = old_cluster.service().component(name='test_component')
    willbegone_component = old_cluster.service_add(name=SERVICE_WILL_BE_REMOVED).component()

    old_cluster.hostcomponent_set((host_1, willbegone_component))
    return build_hc_for_hc_acl_action(
        old_cluster,
        add=((test_component, host_2),),
        remove=((willbegone_component, host_1),),
        add_new_bundle_components=((some_component_id, host_1), (second_component_id, host_1)),
    )


# !===== TESTS =====!


class TestUpgradeActionSectionValidation:
    """Test validation of upgrade action in bundle config"""

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
            ('hc_acl_in_provider', INVALID_OBJECT_DEFINITION),
            ('non_existent_service_in_regular_action', INVALID_ACTION_DEFINITION),
            ('non_existent_component_in_regular_action', INVALID_ACTION_DEFINITION),
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


@create_cluster_from_old_bundle
class TestSuccessfulUpgrade:
    """Test successful scenarios of upgrade actions"""

    @pytest.mark.parametrize(
        'upgrade_name',
        ['simple_upgrade', 'upgrade_with_config', 'upgrade_with_non_default_venv'],
    )
    def test_successful_upgrade(self, upgrade_name, old_cluster: Cluster, sdk_client_fs):
        """Test successful upgrade scenarios"""
        upgrade_config = UPGRADE_EXTRA_ARGS.get(upgrade_name, {})
        self._upgrade_to_newly_uploaded_version(sdk_client_fs, old_cluster, upgrade_name, upgrade_config)

    def test_successful_upgrade_with_content_change(self, sdk_client_fs, old_cluster):
        """
        Test successful upgrade with changing content of action file
        and expect new content to be executed
        """
        upgrade_name = 'file_content_changed'
        expected_message = 'This message came from the new bundle!'
        self._upgrade_to_newly_uploaded_version(sdk_client_fs, old_cluster, upgrade_name, {})
        for job_name in ('before_switch', 'after_switch'):
            job = next(
                filter(
                    lambda x: x.display_name == job_name, sdk_client_fs.job_list()  # pylint: disable=cell-var-from-loop
                )
            )
            assert expected_message in job.log().content, f'"{expected_message}" should be in log'

    @only_clean_adcm
    def test_inventories(self, adcm_fs, sdk_client_fs, old_cluster):
        """Check that inventories of jobs before and after bundle switch are correct"""
        upgrade_name = 'simple_upgrade'
        job_before_id = 1
        job_after_id = 3

        self._upgrade_to_newly_uploaded_version(sdk_client_fs, old_cluster, upgrade_name, {})
        with allure.step('Check inventory of job before the bundle_switch'):
            _compare_inventory_files(adcm_fs, job_before_id)
        with allure.step('Check inventory of job after the bundle_switch'):
            _compare_inventory_files(adcm_fs, job_after_id)

    @only_clean_adcm
    def test_hc_acl(self, adcm_fs, sdk_client_fs, old_cluster, two_hosts):
        """
        Test successful upgrade with `hc_acl` section
        """
        host_1, host_2 = two_hosts
        expected_hc_after_upgrade = {
            (host_1.fqdn, TEST_SERVICE_NAME, 'second_component'),
            (host_1.fqdn, NEW_SERVICE, 'some_component'),
            (host_2.fqdn, TEST_SERVICE_NAME, 'test_component'),
        }
        new_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hc_acl'))

        hc_after_upgrade = _set_hc_and_prepare_new_hc_for_upgrade_action(old_cluster, new_bundle, host_1, host_2)
        self._run_successful_upgrade(new_bundle, old_cluster, 'successful', {'hc': hc_after_upgrade})

        _check_service_is_in_cluster(old_cluster, NEW_SERVICE)
        _check_service_is_in_cluster(old_cluster, TEST_SERVICE_NAME)
        _check_service_is_not_in_cluster(old_cluster, SERVICE_WILL_BE_REMOVED)

        with allure.step('Check hostcomponent'):
            expected_hc = _get_hc_names(old_cluster.hostcomponent())
            sets_are_equal(
                expected_hc,
                expected_hc_after_upgrade,
                'Hostcomponent is not the one that expected after an upgrade with hc_acl',
            )

        self._check_inventories_of_hc_acl_upgrade(adcm_fs, host_1, host_2)

    @allure.step('Check inventories file')
    def _check_inventories_of_hc_acl_upgrade(self, adcm: ADCM, host_1, host_2):
        before_add_group = f'{TEST_SERVICE_NAME}.test_component.add'
        before_remove_group = f'{SERVICE_WILL_BE_REMOVED}.willbegone.remove'
        after_add_group_1 = f'{TEST_SERVICE_NAME}.second_component.add'
        after_add_group_2 = f'{NEW_SERVICE}.some_component.add'

        with allure.step('Check inventory of the job before the bundle switch'):
            before_switch_inventory = get_inventory_file(adcm, 1)
            groups = before_switch_inventory['all']['children']
            assert before_add_group in groups, f'Group {before_add_group} should be in {groups.keys()}'
            assert before_remove_group in groups, f'Group {before_remove_group} should be in {groups.keys()}'
            assert after_add_group_1 not in groups, f'Group {after_add_group_1} should not be in {groups.keys()}'
            assert after_add_group_2 not in groups, f'Group {after_add_group_2} should not be in {groups.keys()}'
            assert host_2.fqdn in (
                hosts := groups[before_add_group]['hosts']
            ), f'Host {host_2.fqdn} should be in group {before_add_group}, but not found in: {hosts}'
            assert host_1.fqdn in (
                hosts := groups[before_remove_group]['hosts']
            ), f'Host {host_1.fqdn} should be in group {before_remove_group}, but not found in {hosts}'

        with allure.step('Check inventory of the job after the bundle switch'):
            after_switch_inventory = get_inventory_file(adcm, 3)
            groups = after_switch_inventory['all']['children']
            assert before_add_group in groups, f'Group {before_add_group} should be in {groups.keys()}'
            assert before_remove_group in groups, f'Group {before_remove_group} should be in {groups.keys()}'
            assert after_add_group_1 not in groups, f'Group {after_add_group_1} should not be in {groups.keys()}'
            assert after_add_group_2 not in groups, f'Group {after_add_group_2} should not be in {groups.keys()}'
            assert host_1.fqdn in (
                hosts := groups[after_add_group_1]['hosts']
            ), f'Host {host_1.fqdn} should be in group {after_add_group_1}, but not found in: {hosts}'
            assert host_1.fqdn in (
                hosts := groups[after_add_group_2]['hosts']
            ), f'Host {host_1.fqdn} should be in group {after_add_group_2}, but not found in {hosts}'
            assert host_2.fqdn not in (
                hosts := groups[before_add_group]['hosts']
            ), f'Host {host_2.fqdn} should not be in group {before_add_group}, but not found in: {hosts}'
            assert host_1.fqdn not in (
                hosts := groups[before_remove_group]['hosts']
            ), f'Host {host_1.fqdn} should not be in group {before_remove_group}, but not found in {hosts}'

    # pylint: disable=too-many-arguments
    def _upgrade_to_newly_uploaded_version(
        self, client, old_cluster, upgrade_name, upgrade_config, new_bundle_dirs=('successful', 'new')
    ):
        with allure.step('Upload new version of cluster bundle'):
            new_bundle = client.upload_from_fs(get_data_dir(__file__, *new_bundle_dirs))
        self._run_successful_upgrade(new_bundle, old_cluster, upgrade_name, upgrade_config)

    def _run_successful_upgrade(self, new_bundle, old_cluster, upgrade_name, upgrade_config):
        with allure.step('Run upgrade and expect it to be successful'):
            upgrade_task = old_cluster.upgrade(name=upgrade_name).do(**upgrade_config)
            assert upgrade_task.wait() == 'success', f'Upgrade {upgrade_name} failed unexpectedly'
            check_state(old_cluster, 'ready_to_upgrade')
        with allure.step('Check that prototype was upgraded successfully'):
            check_prototype(old_cluster, new_bundle.cluster_prototype().id)
            check_cluster_objects_configs_equal_bundle_default(old_cluster, new_bundle)


@pytest.mark.parametrize('old_cluster', [(FAILURES_DIR, 'old')], indirect=True, ids=['failures_old_bundle'])
class TestFailedUpgradeAction:
    """Test cases when upgrade action is failed during execution"""

    def test_fail_before_switch(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails before bundle_switch was performed
        """
        old_bundle = old_cluster.bundle()
        expected_state = old_cluster.state
        expected_before_upgrade_state = expected_state
        expected_prototype_id = old_cluster.prototype_id

        self._upload_new_version(sdk_client_fs, 'before_switch')
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_before_upgrade_state(old_cluster, expected_before_upgrade_state)
        check_prototype(old_cluster, expected_prototype_id)
        check_cluster_objects_configs_equal_bundle_default(old_cluster, old_bundle)

    def test_fail_after_switch_with_on_fail(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails after bundle_switch was performed.
        Failed job has "on_fail" directive.
        """
        restore_action_name = 'restore'
        expected_state = 'something_is_wrong'
        expected_state_after_restore = 'upgraded'
        expected_before_upgrade_state = old_cluster.state

        bundle = self._upload_new_version(sdk_client_fs, 'after_switch_with_on_fail')
        expected_prototype_id = bundle.cluster_prototype().id
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_before_upgrade_state(old_cluster, expected_before_upgrade_state)
        check_prototype(old_cluster, expected_prototype_id)
        check_cluster_objects_configs_equal_bundle_default(old_cluster, bundle)
        self._check_action_list(old_cluster, {restore_action_name})
        run_cluster_action_and_assert_result(old_cluster, restore_action_name)
        check_state(old_cluster, expected_state_after_restore)

    def test_fail_after_switch_without_on_fail(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails after bundle_switch was performed.
        Failed job doesn't have "on_fail" directive.
        """
        expected_state = old_cluster.state
        expected_before_upgrade_state = expected_state

        bundle = self._upload_new_version(sdk_client_fs, 'after_switch')
        expected_prototype_id = bundle.cluster_prototype().id
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_before_upgrade_state(old_cluster, expected_before_upgrade_state)
        check_prototype(old_cluster, expected_prototype_id)
        check_cluster_objects_configs_equal_bundle_default(old_cluster, bundle)
        self._check_action_list(old_cluster, set())

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

    def test_hc_acl_fail_before_switch(self, sdk_client_fs, old_cluster, two_hosts):
        """
        Test an upgrade with `hc_acl` failed before the bundle switch
        """
        host_1, host_2 = two_hosts

        new_bundle = self._upload_new_version(sdk_client_fs, 'hc_acl')
        hc_argument = _set_hc_and_prepare_new_hc_for_upgrade_action(old_cluster, new_bundle, host_1, host_2)
        expected_hc = _get_hc_names(old_cluster.hostcomponent())

        self._upgrade_and_expect_state(old_cluster, 'created', name='fail before switch', hc=hc_argument)

        _check_service_is_in_cluster(old_cluster, TEST_SERVICE_NAME)
        _check_service_is_in_cluster(old_cluster, SERVICE_WILL_BE_REMOVED)
        _check_service_is_not_in_cluster(old_cluster, NEW_SERVICE)

        actual_hc = _get_hc_names(old_cluster.hostcomponent())
        sets_are_equal(actual_hc, expected_hc, 'The hostcomponent from before the upgrade was expected')

    @pytest.mark.parametrize(
        'upgrade_name', ['fail after switch', 'fail on first action after switch'], ids=lambda x: x.replace(' ', '_')
    )
    def test_hc_acl_fail_after_switch(self, upgrade_name: str, sdk_client_fs, old_cluster, two_hosts):
        """
        Test an upgrade with `hc_acl` failed after the bundle switch
        """
        host_1, host_2 = two_hosts
        expected_hc = {(host_2.fqdn, TEST_SERVICE_NAME, 'test_component')}

        new_bundle = self._upload_new_version(sdk_client_fs, 'hc_acl')
        hc_argument = _set_hc_and_prepare_new_hc_for_upgrade_action(old_cluster, new_bundle, host_1, host_2)

        self._upgrade_and_expect_state(old_cluster, 'created', name=upgrade_name, hc=hc_argument)

        _check_service_is_in_cluster(old_cluster, TEST_SERVICE_NAME)
        _check_service_is_in_cluster(old_cluster, NEW_SERVICE)
        _check_service_is_not_in_cluster(old_cluster, SERVICE_WILL_BE_REMOVED)

        actual_hc = _get_hc_names(old_cluster.hostcomponent())
        sets_are_equal(actual_hc, expected_hc, 'The hostcomponent from hc argument for an upgrade')

    @allure.step('Upload new version of cluster bundle')
    def _upload_new_version(self, client: ADCMClient, name: str) -> Bundle:
        """Upload new version of bundle based on the given bundle file_name"""
        return client.upload_from_fs(get_data_dir(__file__, FAILURES_DIR, name))

    @allure.step('Upgrade cluster and expect it to enter the "{state}" state')
    def _upgrade_and_expect_state(self, cluster: Cluster, state: str, **kwargs):
        """
        Upgrade cluster to a new version (expect upgrade to fail)
        and check if it's state is correct
        """
        task = cluster.upgrade(**kwargs).do()
        assert task.wait() == 'failed', 'Upgrade action should have failed'
        check_state(cluster, state)

    @allure.step('Check that cluster have "before_upgrade" equal to {state}')
    def _check_before_upgrade_state(self, cluster: Cluster, state: str):
        cluster.reread()
        assert (
            actual_state := cluster.before_upgrade['state']
        ) == state, f'"before_upgrade" should be {state}, not {actual_state}'

    @allure.step('Check list of available actions on cluster')
    def _check_action_list(self, cluster: Cluster, action_names: Set[str]):
        """Check that action list is equal to given one (by names)"""
        cluster.reread()
        presented_action_names = {a.name for a in cluster.action_list()}
        sets_are_equal(presented_action_names, action_names, message='Incorrect action list')


# pylint: disable-next=too-few-public-methods
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
