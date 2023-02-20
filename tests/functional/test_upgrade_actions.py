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
from collections.abc import Collection
from pathlib import Path

import allure
import pytest
import yaml
from adcm_client.objects import ADCMClient, Bundle, Cluster, Component, Host, Service
from adcm_pytest_plugin.docker.adcm import ADCM
from adcm_pytest_plugin.docker.utils import get_file_from_container
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    wait_for_task_and_assert_result,
)
from adcm_pytest_plugin.utils import (
    catch_failed,
    get_data_dir,
    parametrize_by_data_subdirs,
    random_string,
)
from coreapi.exceptions import ErrorMessage

from tests.functional.tools import build_hc_for_hc_acl_action, get_inventory_file
from tests.library.assertions import (
    expect_api_error,
    expect_no_api_error,
    sets_are_equal,
)
from tests.library.errorcodes import (
    COMPONENT_CONSTRAINT_ERROR,
    INVALID_ACTION_DEFINITION,
    INVALID_OBJECT_DEFINITION,
    INVALID_UPGRADE_DEFINITION,
)

# pylint: disable=redefined-outer-name

TEST_SERVICE_NAME = "test_service"
FAILURES_DIR = "upgrade_failures"
NEW_SERVICE = "new_service"
SERVICE_WILL_BE_REMOVED = "will_be_removed"

UPGRADE_EXTRA_ARGS = {"upgrade_with_config": {"config": {"parampampam": "somestring"}}}


# !===== FUNCS =====!


create_cluster_from_old_bundle = pytest.mark.parametrize(
    "old_cluster",
    [("successful", "old")],
    indirect=True,
    ids=["successful_old_bundle"],
)


def _create_old_cluster(client, *dirs):
    bundle = client.upload_from_fs(get_data_dir(__file__, *dirs))
    cluster = bundle.cluster_create("Test Cluster for Upgrade")
    cluster.service_add(name=TEST_SERVICE_NAME)
    return cluster


@pytest.fixture()
def old_cluster(request, sdk_client_fs) -> Cluster:
    """Upload old cluster bundle and then create one"""
    return _create_old_cluster(sdk_client_fs, *request.param)


@pytest.fixture()
def two_hosts(sdk_client_fs, old_cluster) -> tuple[Host, Host]:
    """Two hosts created and added to an old cluster"""
    provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
    provider = provider_bundle.provider_create(name="Too Simple Provider")
    return old_cluster.host_add(provider.host_create("first-host")), old_cluster.host_add(
        provider.host_create("second-host"),
    )


@allure.step('Check cluster state is equal to "{state}"')
def check_state(cluster: Cluster, state: str):
    """Check state of a cluster"""
    cluster.reread()
    assert (actual_state := cluster.state) == state, f"State after failed upgrade should be {state}, not {actual_state}"


@allure.step("Check that cluster prototype is equal to {expected_prototype_id}")
def check_prototype(cluster: Cluster, expected_prototype_id: int):
    """Check that prototype of a cluster is the same as expected"""
    cluster.reread()
    assert (
        actual_id := cluster.prototype_id
    ) == expected_prototype_id, f"Prototype of cluster should be {expected_prototype_id}, not {actual_id}"


def check_cluster_objects_configs_equal_bundle_default(
    cluster: Cluster,
    bundle: Bundle,
    *,
    service_names: tuple[str, ...] = (TEST_SERVICE_NAME,),
):
    """
    Check that configurations of cluster, its services and components
    are equal to configurations of newly created cluster from given bundle
    """
    with allure.step(
        f"Check configuration of cluster {cluster.name} "
        f"is equal to default configuration of cluster from {bundle.name}",
    ):
        actual_configs = _extract_configs(cluster)
        cluster_with_defaults = bundle.cluster_create(f"Cluster to take config from {random_string(4)}")
        for service in service_names:
            cluster_with_defaults.service_add(name=service)
        expected_configs = _extract_configs(cluster_with_defaults)

        if actual_configs == expected_configs:
            return
        allure.attach(
            json.dumps(expected_configs, indent=2),
            name="Expected cluster objects configuration",
            attachment_type=allure.attachment_type.JSON,
        )
        allure.attach(
            json.dumps(actual_configs, indent=2),
            name="Actual cluster objects configuration",
            attachment_type=allure.attachment_type.JSON,
        )
        raise AssertionError("Cluster objects' configs aren't equal to expected, check attachments for more details")


def _compare_inventory_files(adcm_fs, job_id: int):
    """Compare two inventory files: one from local storage (expected) and one from docker container with ADCM"""
    inventory_file = get_file_from_container(adcm_fs, f"/adcm/data/run/{job_id}/", "inventory.json")
    actual_inventory = json.loads(inventory_file.read().decode("utf-8"))
    with open(get_data_dir(__file__, "successful", f"inventory_{job_id}.json"), "rb") as file:
        expected_inventory = json.load(file)
    if actual_inventory == expected_inventory:
        return
    allure.attach(
        json.dumps(expected_inventory, indent=2),
        name=f"Expected inventory of job {job_id}",
        attachment_type=allure.attachment_type.JSON,
    )
    allure.attach(
        json.dumps(actual_inventory, indent=2),
        name=f"Actual inventory of job {job_id}",
        attachment_type=allure.attachment_type.JSON,
    )
    raise AssertionError(f"Inventories should be equal for job {job_id}.\nSee attachments for more details.")


def _extract_configs(cluster: Cluster):
    """Extract configurations of the cluster, its services and components as dict"""
    return {
        "config": dict(cluster.config()),
        "services": {
            service.name: {
                "config": dict(service.config()),
                "components": {
                    component.name: {"config": dict(component.config())} for component in service.component_list()
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


def _get_hc_names(hc_map) -> set[tuple[str, str, str]]:
    return {(x["host"], x["service_name"], x["component"]) for x in hc_map}


def _get_component_prototype_id(bundle, service_name, component_name) -> int:
    service_proto = bundle.service_prototype(name=service_name)
    component = next((c for c in service_proto.components if c["name"] == component_name), None)
    if component is None:
        raise ValueError(f'Component "{component_name}" is not presented in prototype of service "{service_name}"')
    return component["id"]


def _set_hc_and_prepare_new_hc_for_upgrade_action(old_cluster, new_bundle, host_1, host_2):
    second_component_id = _get_component_prototype_id(new_bundle, TEST_SERVICE_NAME, "second_component")
    some_component_id = _get_component_prototype_id(new_bundle, NEW_SERVICE, "some_component")
    test_component = old_cluster.service().component(name="test_component")
    willbegone_component = old_cluster.service_add(name=SERVICE_WILL_BE_REMOVED).component()

    old_cluster.hostcomponent_set((host_1, willbegone_component))
    return build_hc_for_hc_acl_action(
        old_cluster,
        add=((test_component, host_2),),
        remove=(),
        add_new_bundle_components=((some_component_id, host_1), (second_component_id, host_1)),
    )


# !===== TESTS =====!


class TestUpgradeActionSectionValidation:
    """Test validation of upgrade action in bundle config"""

    @parametrize_by_data_subdirs(__file__, "validation", "valid")
    def test_validation_succeed_on_upload(self, sdk_client_fs, path):
        """Test that valid bundles with upgrade actions succeed to upload"""
        verbose_bundle_name = os.path.basename(path).replace("_", " ").capitalize()
        with allure.step(f'Upload bundle "{verbose_bundle_name}" and expect it to succeed'), catch_failed(
            ErrorMessage,
            f'Bundle "{verbose_bundle_name}" should be uploaded successfully',
        ):
            bundle = sdk_client_fs.upload_from_fs(path)
            bundle.delete()

    @pytest.mark.parametrize(
        ("bundle_dir_name", "expected_error"),
        [
            ("bundle_switch_in_regular_actions", INVALID_OBJECT_DEFINITION),
            ("incorrect_internal_action", INVALID_UPGRADE_DEFINITION),
            ("no_bundle_switch", INVALID_UPGRADE_DEFINITION),
            ("hc_acl_in_provider", INVALID_OBJECT_DEFINITION),
            ("non_existent_service_in_regular_action", INVALID_ACTION_DEFINITION),
            ("non_existent_component_in_regular_action", INVALID_ACTION_DEFINITION),
        ],
    )
    def test_validation_failed_on_upload(self, bundle_dir_name, expected_error, sdk_client_fs):
        """Test that invalid bundles with upgrade actions fails to upload"""
        verbose_bundle_name = bundle_dir_name.replace("_", " ").capitalize()
        invalid_bundle_file = get_data_dir(__file__, "validation", "invalid", bundle_dir_name)
        with allure.step(f'Upload bundle "{verbose_bundle_name}" and expect upload to fail'):
            with pytest.raises(ErrorMessage) as e:
                sdk_client_fs.upload_from_fs(invalid_bundle_file)
            expected_error.equal(e)


@create_cluster_from_old_bundle
class TestSuccessfulUpgrade:
    """Test successful scenarios of upgrade actions"""

    @pytest.mark.parametrize(
        "upgrade_name",
        ["simple_upgrade", "upgrade_with_config", "upgrade_with_non_default_venv"],
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
        upgrade_name = "file_content_changed"
        expected_message = "This message came from the new bundle!"
        self._upgrade_to_newly_uploaded_version(sdk_client_fs, old_cluster, upgrade_name, {})
        for job_name in ("before_switch", "after_switch"):
            job = next(
                filter(
                    lambda x: x.display_name == job_name,  # pylint: disable=cell-var-from-loop
                    sdk_client_fs.job_list(),
                ),
            )
            assert expected_message in job.log().content, f'"{expected_message}" should be in log'

    def test_inventories(self, adcm_fs, sdk_client_fs, old_cluster):
        """Check that inventories of jobs before and after bundle switch are correct"""
        upgrade_name = "simple_upgrade"
        job_before_id = 1
        job_after_id = 3

        self._upgrade_to_newly_uploaded_version(sdk_client_fs, old_cluster, upgrade_name, {})
        with allure.step("Check inventory of job before the bundle_switch"):
            _compare_inventory_files(adcm_fs, job_before_id)
        with allure.step("Check inventory of job after the bundle_switch"):
            _compare_inventory_files(adcm_fs, job_after_id)

    def test_hc_acl(self, adcm_fs, sdk_client_fs, old_cluster, two_hosts):
        """
        Test successful upgrade with `hc_acl` section
        """
        host_1, host_2 = two_hosts
        expected_hc_after_upgrade = {
            (host_1.fqdn, TEST_SERVICE_NAME, "second_component"),
            (host_1.fqdn, NEW_SERVICE, "some_component"),
            (host_2.fqdn, TEST_SERVICE_NAME, "test_component"),
        }
        new_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hc_acl"))

        hc_after_upgrade = _set_hc_and_prepare_new_hc_for_upgrade_action(old_cluster, new_bundle, host_1, host_2)
        self._run_successful_upgrade(
            new_bundle,
            old_cluster,
            "successful",
            {"hc": hc_after_upgrade},
            service_names=(TEST_SERVICE_NAME, NEW_SERVICE),
        )

        _check_service_is_in_cluster(old_cluster, NEW_SERVICE)
        _check_service_is_in_cluster(old_cluster, TEST_SERVICE_NAME)
        _check_service_is_not_in_cluster(old_cluster, SERVICE_WILL_BE_REMOVED)

        with allure.step("Check hostcomponent"):
            expected_hc = _get_hc_names(old_cluster.hostcomponent())
            sets_are_equal(
                expected_hc,
                expected_hc_after_upgrade,
                "Hostcomponent is not the one that expected after an upgrade with hc_acl",
            )

        self._check_inventories_of_hc_acl_upgrade(adcm_fs, host_1, host_2)

    @allure.step("Check inventory files")  # pylint: disable-next=too-many-locals
    def _check_inventories_of_hc_acl_upgrade(self, adcm: ADCM, host_1, host_2):
        test_component_group = f"{TEST_SERVICE_NAME}.test_component"
        before_add_group = f"{test_component_group}.add"
        willbegone_group = f"{SERVICE_WILL_BE_REMOVED}.willbegone"
        before_remove_group = f"{willbegone_group}.remove"

        second_component_group = f"{TEST_SERVICE_NAME}.second_component"
        after_add_group_1 = f"{second_component_group}.add"
        some_component_group = f"{NEW_SERVICE}.some_component"
        after_add_group_2 = f"{some_component_group}.add"

        with allure.step("Check inventory of the job before the bundle switch"):
            before_switch_inventory = get_inventory_file(adcm, 1)
            groups = before_switch_inventory["all"]["children"]
            for group_name in (before_add_group, willbegone_group, test_component_group):
                self._check_group_is_presented(group_name, groups)
            for group_name in (before_remove_group, after_add_group_1, after_add_group_2):
                self._check_group_is_absent(group_name, groups)
            self._check_host_is_in_group(host_2, before_add_group, groups)
            self._check_host_is_in_group(host_2, test_component_group, groups)
            self._check_host_is_in_group(host_1, willbegone_group, groups)

        with allure.step("Check inventory of the job after the bundle switch"):
            after_switch_inventory = get_inventory_file(adcm, 4)
            groups = after_switch_inventory["all"]["children"]
            self._check_group_is_presented(test_component_group, groups)
            self._check_group_is_presented(after_add_group_1, groups)
            self._check_group_is_presented(second_component_group, groups)
            self._check_group_is_presented(after_add_group_2, groups)
            self._check_group_is_presented(some_component_group, groups)
            self._check_group_is_absent(before_add_group, groups)
            self._check_group_is_absent(before_remove_group, groups)
            self._check_group_is_absent(willbegone_group, groups)
            self._check_host_is_in_group(host_1, after_add_group_1, groups)
            self._check_host_is_in_group(host_1, after_add_group_2, groups)
            self._check_host_is_in_group(host_1, after_add_group_1, groups)
            self._check_host_is_in_group(host_1, second_component_group, groups)
            self._check_host_is_in_group(host_1, some_component_group, groups)

    def _upgrade_to_newly_uploaded_version(
        self,
        client,
        old_cluster,
        upgrade_name,
        upgrade_config,
        new_bundle_dirs=("successful", "new"),
    ):
        with allure.step("Upload new version of cluster bundle"):
            new_bundle = client.upload_from_fs(get_data_dir(__file__, *new_bundle_dirs))
        self._run_successful_upgrade(new_bundle, old_cluster, upgrade_name, upgrade_config)

    def _run_successful_upgrade(self, new_bundle, old_cluster, upgrade_name, upgrade_config, **check_kwargs):
        with allure.step("Run upgrade and expect it to be successful"):
            upgrade_task = old_cluster.upgrade(name=upgrade_name).do(**upgrade_config)
            assert upgrade_task.wait() == "success", f"Upgrade {upgrade_name} failed unexpectedly"
            check_state(old_cluster, "ready_to_upgrade")
        with allure.step("Check that prototype was upgraded successfully"):
            check_prototype(old_cluster, new_bundle.cluster_prototype().id)
            check_cluster_objects_configs_equal_bundle_default(old_cluster, new_bundle, **check_kwargs)

    @staticmethod
    def _check_group_is_presented(group_name, groups):
        assert group_name in groups, f"Group {group_name} should be in {groups.keys()}"

    @staticmethod
    def _check_group_is_absent(group_name, groups):
        assert group_name not in groups, f"Group {group_name} should not be in {groups.keys()}"

    @staticmethod
    def _check_host_is_in_group(host, group_name, groups):
        assert host.fqdn in (
            hosts := groups[group_name]["hosts"]
        ), f"Host {host.fqdn} should be in group {group_name}, but not found in: {hosts}"


class FailedUploadMixin:
    """Useful methods for upload failures tests"""

    @allure.step("Upload new version of cluster bundle")
    def _upload_new_version(self, client: ADCMClient, name: str, directories: tuple = (FAILURES_DIR,)) -> Bundle:
        """Upload new version of bundle based on the given bundle file_name"""
        return client.upload_from_fs(get_data_dir(__file__, *directories, name))

    @allure.step('Upgrade cluster and expect it to enter the "{state}" state')
    def _upgrade_and_expect_state(self, cluster: Cluster, state: str, name: str | None = None, **kwargs):
        """
        Upgrade cluster to a new version (expect upgrade to fail)
        and check if it's state is correct
        """
        task = (cluster.upgrade(name=name) if name is not None else cluster.upgrade()).do(**kwargs)
        assert task.wait() == "failed", "Upgrade action should have failed"
        check_state(cluster, state)

    @allure.step('Check that cluster have "before_upgrade" equal to {state}')
    def _check_before_upgrade_state(self, cluster: Cluster, state: str):
        cluster.reread()
        assert (
            actual_state := cluster.before_upgrade["state"]
        ) == state, f'"before_upgrade" should be {state}, not {actual_state}'

    @allure.step("Check list of available actions on cluster")
    def _check_action_list(self, cluster: Cluster, action_names: set[str]):
        """Check that action list is equal to given one (by names)"""
        cluster.reread()
        presented_action_names = {a.name for a in cluster.action_list()}
        sets_are_equal(presented_action_names, action_names, message="Incorrect action list")


@pytest.mark.parametrize("old_cluster", [(FAILURES_DIR, "old")], indirect=True, ids=["failures_old_bundle"])
class TestFailedUpgradeAction(FailedUploadMixin):
    """Test cases when upgrade action is failed during execution"""

    def test_fail_before_switch(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails before bundle_switch was performed
        """
        old_bundle = old_cluster.bundle()
        expected_state = old_cluster.state
        expected_before_upgrade_state = expected_state
        expected_prototype_id = old_cluster.prototype_id

        self._upload_new_version(sdk_client_fs, "before_switch")
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_before_upgrade_state(old_cluster, expected_before_upgrade_state)
        check_prototype(old_cluster, expected_prototype_id)
        check_cluster_objects_configs_equal_bundle_default(old_cluster, old_bundle)

    def test_fail_after_switch_with_on_fail(self, sdk_client_fs, old_cluster):
        """
        Test bundle action fails after bundle_switch was performed.
        Failed job has "on_fail" directive.
        """
        restore_action_name = "restore"
        expected_state = "something_is_wrong"
        expected_state_after_restore = "upgraded"
        expected_before_upgrade_state = old_cluster.state

        bundle = self._upload_new_version(sdk_client_fs, "after_switch_with_on_fail")
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

        bundle = self._upload_new_version(sdk_client_fs, "after_switch")
        expected_prototype_id = bundle.cluster_prototype().id
        self._upgrade_and_expect_state(old_cluster, expected_state)
        self._check_before_upgrade_state(old_cluster, expected_before_upgrade_state)
        check_prototype(old_cluster, expected_prototype_id)
        check_cluster_objects_configs_equal_bundle_default(old_cluster, bundle)
        self._check_action_list(old_cluster, set())

    @pytest.mark.parametrize(
        "upgrade_name",
        ["fail_after_bundle_switch", "fail_before_bundle_switch"],
        ids=["fail_before_switch", "fail_after_switch"],
    )
    def test_fail_with_both_action_states_set(self, upgrade_name: str, sdk_client_fs, old_cluster):
        """
        Test bundle action fails before/after bundle_switch
        when both on_success and on_fail are presented in action block
        """
        self._upload_new_version(sdk_client_fs, "upgrade_action_has_on_fail")
        self._upgrade_and_expect_state(old_cluster, "something_failed", name=upgrade_name)


@create_cluster_from_old_bundle
class TestUpgradeWithHCFailures(FailedUploadMixin):
    """Test upgrades failures with `hc_acl` in upgrade"""

    @pytest.mark.parametrize(
        "upgrade_name",
        ["fail after switch", "fail on first action after switch"],
        ids=lambda x: x.replace(" ", "_"),
    )
    def test_hc_acl_fail_after_switch(self, upgrade_name: str, sdk_client_fs, old_cluster, two_hosts):
        """
        Test an upgrade with `hc_acl` failed after the bundle switch
        """
        host_1, host_2 = two_hosts
        expected_hc = {(host_2.fqdn, TEST_SERVICE_NAME, "test_component")}

        new_bundle = self._upload_new_version(sdk_client_fs, "hc_acl", ())
        hc_argument = _set_hc_and_prepare_new_hc_for_upgrade_action(old_cluster, new_bundle, host_1, host_2)

        self._upgrade_and_expect_state(old_cluster, "created", name=upgrade_name, hc=hc_argument)

        _check_service_is_in_cluster(old_cluster, TEST_SERVICE_NAME)
        _check_service_is_in_cluster(old_cluster, NEW_SERVICE)
        _check_service_is_not_in_cluster(old_cluster, SERVICE_WILL_BE_REMOVED)

        actual_hc = _get_hc_names(old_cluster.hostcomponent())
        sets_are_equal(actual_hc, expected_hc, "The hostcomponent from hc argument for an upgrade")

    def test_hc_acl_fail_before_switch(self, sdk_client_fs, old_cluster, two_hosts):
        """
        Test an upgrade with `hc_acl` failed before the bundle switch
        """
        host_1, host_2 = two_hosts

        new_bundle = self._upload_new_version(sdk_client_fs, "hc_acl", ())
        hc_argument = _set_hc_and_prepare_new_hc_for_upgrade_action(old_cluster, new_bundle, host_1, host_2)
        expected_hc = _get_hc_names(old_cluster.hostcomponent())

        self._upgrade_and_expect_state(old_cluster, "created", name="fail before switch", hc=hc_argument)

        _check_service_is_in_cluster(old_cluster, TEST_SERVICE_NAME)
        _check_service_is_in_cluster(old_cluster, SERVICE_WILL_BE_REMOVED)
        _check_service_is_not_in_cluster(old_cluster, NEW_SERVICE)

        actual_hc = _get_hc_names(old_cluster.hostcomponent())
        sets_are_equal(actual_hc, expected_hc, "The hostcomponent from before the upgrade was expected")


class TestUpgradeActionRelations:
    """Test cases when upgrade action"""

    @pytest.mark.parametrize(
        ("folder_dir", "file_dir"),
        [
            ("upgrade_failures", "before_switch"),
            ("upgrade_success", "after_switch"),
        ],
    )
    def test_check_upgrade_actions_relations(self, sdk_client_fs, folder_dir, file_dir):
        """
        Test bundle action fails before bundle_switch was performed
        """

        jobs_before = sdk_client_fs.job_list()
        logs_before = [log for data in jobs_before for log in data.log_files]
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, folder_dir, "old"))
        cluster = bundle.cluster_create("Test Cluster for Upgrade")
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
                len({"first action after switch", "switch action", "first_action"} & {j.display_name for j in jobs})
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
                {"dummy_action", "restore"} if "success" in folder_dir else {"dummy_action"}
            ), "Not all actions avaliable"


def _set_ids_for_upload_bundles_set_hc(item):
    # is set_hc
    if isinstance(item, int):
        return f"component_on_all_{item}_hosts"
    if isinstance(item, Collection):
        # is upload_bundles
        if isinstance(item[0], list):
            old_constraint = str(item[0]).replace(" ", "").replace("'", "")
            new_constraint = str(item[1]).replace(" ", "").replace("'", "")
            return f"change_constraint_from_{old_constraint}_to_{new_constraint}"
        # is set_hc with 2 args
        return f"component_on_{item[0]}_hosts_out_of_{item[1]}"
    return str(item)


class TestConstraintsChangeAfterUpgrade:
    """
    Test upgrade when constraints are changed in new version
    """

    OLD_CLUSTER = {"type": "cluster", "name": "cluster_with_constraints", "version": "1.0"}
    NEW_CLUSTER = {**OLD_CLUSTER, "version": "2.0"}
    SERVICE_DESC = {"type": "service", "name": "service_with_constraints", "version": "1.0"}
    COMPONENT_NAME = "component"
    DUMMY_COMPONENT_NAME = "dummy"

    NO_HC_ACL_UPGRADE_SECTION = {
        "name": "Simple upgrade",
        "versions": {"min": 0.5, "max": 1.9},
        "states": {"available": "any"},
        "scripts": [
            {"name": "before", "script": "./succeed.yaml", "script_type": "ansible"},
            {"name": "switch", "script": "bundle_switch", "script_type": "internal"},
            {"name": "after", "script": "./succeed.yaml", "script_type": "ansible"},
        ],
    }

    @pytest.fixture(scope="session")
    def dummy_action_content(self) -> str:
        """Read dummy action file"""
        bundle_dir = Path(get_data_dir(__file__, "constraints", "new"))
        return (bundle_dir / "succeed.yaml").read_text(encoding="utf-8")

    @pytest.fixture()
    def with_hc_in_upgrade(self, request) -> bool:
        """Flag to prepare `hc_acl` in bundle"""
        return bool(request.param)

    @pytest.fixture()
    def cluster_with_new_component(self, sdk_client_fs) -> tuple[Cluster, Service, Component]:
        """Upload bundles from data dir, create service from old bundle, add service to it"""
        old_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "constraints", "old"))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "constraints", "new"))
        cluster = old_bundle.cluster_create("Test Cluster")
        service = cluster.service_add(name=self.SERVICE_DESC["name"])
        return cluster, service, service.component()

    @pytest.fixture()
    def hc_acl_block(self, request) -> dict:
        """Define `hc_acl` block for upgrade"""
        if hasattr(request, "param") and request.param:
            return request.param
        return {
            "hc_acl": [
                {
                    "service": self.SERVICE_DESC["name"],
                    "component": self.COMPONENT_NAME,
                    "action": "add",
                },
            ],
        }

    @pytest.fixture()
    def upload_bundles(
        self,
        request,
        sdk_client_fs,
        tmpdir,
        with_hc_in_upgrade,
        hc_acl_block,
        dummy_action_content,
    ) -> tuple[Bundle, Bundle]:
        """Upload bundles created dynamically based on the given constraints"""
        # request.param should be like ([0,1], ['+'])
        old_constraint, new_constraint = request.param
        with allure.step(f"Preparing bundles: constraint in old {old_constraint}, constraint in new {new_constraint}"):
            old_bundle_config = [
                self.OLD_CLUSTER,
                {
                    **self.SERVICE_DESC,
                    # old constraint may be []
                    "components": {
                        self.COMPONENT_NAME: ({"constraint": old_constraint} if old_constraint else {}),
                        self.DUMMY_COMPONENT_NAME: {},
                    },
                },
            ]
            new_bundle_config = [
                {
                    **self.NEW_CLUSTER,
                    "upgrade": [
                        {
                            **self.NO_HC_ACL_UPGRADE_SECTION,
                            **(hc_acl_block if with_hc_in_upgrade else {}),
                        },
                    ],
                },
                {
                    **self.SERVICE_DESC,
                    "components": {
                        self.COMPONENT_NAME: ({"constraint": new_constraint} if new_constraint else {}),
                        self.DUMMY_COMPONENT_NAME: {},
                    },
                },
            ]
            tdir = Path(tmpdir)
            old_path = tdir / "old"
            old_path.mkdir()
            with (old_path / "config.yaml").open("w") as f:
                yaml.safe_dump(old_bundle_config, f)
            new_path = tdir / "new"
            new_path.mkdir()
            with (new_path / "config.yaml").open("w") as f:
                yaml.safe_dump(new_bundle_config, f)
            (new_path / "succeed.yaml").write_text(dummy_action_content, encoding="utf-8")
        with allure.step("Upload old and new bundles"):
            return sdk_client_fs.upload_from_fs(old_path), sdk_client_fs.upload_from_fs(new_path)

    @allure.step("Create cluster from old bundle and add service")
    @pytest.fixture()
    def cluster_with_component(self, upload_bundles) -> tuple[Cluster, Component]:
        """Create cluster and add service"""
        old_bundle, _ = upload_bundles
        cluster = old_bundle.cluster_create("Cluster with constraints")
        service = cluster.service_add(name=self.SERVICE_DESC["name"])
        return cluster, service.component(name=self.COMPONENT_NAME)

    @allure.title("Create hosts and set hostcomponent")
    @pytest.fixture()
    def _set_hc(self, request, cluster_with_component, generic_provider) -> None:
        """Set hostcomponent based on given component on host / hosts in cluster amount"""
        # total amount of hosts shouldn't be 0, it'll conflict with dummy component
        if isinstance(request.param, int):
            hosts_per_component = hosts_in_cluster = request.param
        elif isinstance(request.param, tuple) and all(isinstance(i, int) for i in request.param):
            hosts_per_component, hosts_in_cluster = request.param
        else:
            raise ValueError("Check `set_hc` and give correct param values IDHTFCE")
        cluster, component = cluster_with_component
        with allure.step(f"Create {hosts_in_cluster} and add all of them to a cluster"):
            hosts = [cluster.host_add(generic_provider.host_create(f"host-{i}")) for i in range(hosts_in_cluster)]
        with allure.step(f"Map component to {hosts_per_component} hosts and add dummy component on one of the hosts"):
            cluster.hostcomponent_set(
                (hosts[0], cluster.service().component(name=self.DUMMY_COMPONENT_NAME)),
                *[(h, component) for h in hosts[:hosts_per_component]],
            )

    # wrap it in something readable
    @pytest.mark.parametrize("with_hc_in_upgrade", [True, False], indirect=True, ids=lambda i: f"with_hc_acl_{i}")
    @pytest.mark.parametrize(
        ("upload_bundles", "_set_hc"),
        [
            # from many hosts to 1
            ((["+"], [1]), 2),
            (([1, "+"], [1]), 2),
            (([1, 2], [1]), 2),
            (([1, "odd"], [1]), 3),
            # from fewer to greater
            ((["+"], ["odd"]), 2),
            (([1, "+"], ["+"]), (2, 3)),
            (([0, 1], [1]), (0, 1)),
            (([0, 1], [1, "+"]), (0, 1)),
            (([0, 1], ["+"]), (0, 1)),
            (([0, "+"], ["+"]), (0, 2)),
            # new constraint
            (([], [1]), (0, 1)),
            (([], [1, 2]), (0, 1)),
            (([], ["odd"]), (0, 1)),
            (([], ["odd"]), 2),
            (([], ["+"]), (0, 1)),
            (([], [1, "+"]), (0, 1)),
        ],
        indirect=True,
        ids=_set_ids_for_upload_bundles_set_hc,
    )
    @pytest.mark.usefixtures("_set_hc", "upload_bundles")
    def test_incorrect_hc_in_upgrade_with_actions(self, sdk_client_fs, cluster_with_component, with_hc_in_upgrade):
        """
        Test that when incorrect for new constraints HC is set,
        upgrade with actions won't start
        """
        cluster, _ = cluster_with_component
        hc_or_not = {"hc": build_hc_for_hc_acl_action(cluster)} if with_hc_in_upgrade else {}
        expect_api_error(
            "upgrade cluster with hc not suitable for new bundle version",
            cluster.upgrade().do,
            **hc_or_not,
            err_=COMPONENT_CONSTRAINT_ERROR,
            err_args_=[
                'component "component"',
                f'in host component list for service {self.SERVICE_DESC["name"]}',
            ],
        )
        with allure.step("Check no actions were launched"):
            assert len(sdk_client_fs.job_list()) == 0, "At least one action has been launched. None should."

    @pytest.mark.parametrize("with_hc_in_upgrade", [True], indirect=True, ids=lambda i: f"with_hc_acl_{i}")
    @pytest.mark.parametrize(
        "hc_acl_block",
        [
            {
                "hc_acl": [
                    {
                        "service": SERVICE_DESC["name"],
                        "component": COMPONENT_NAME,
                        "action": "remove",
                    },
                ],
            },
        ],
    )
    @pytest.mark.parametrize(
        ("upload_bundles", "_set_hc"),
        [(([1], []), 1)],
        indirect=True,
        ids=_set_ids_for_upload_bundles_set_hc,
    )
    @pytest.mark.usefixtures("_set_hc", "upload_bundles", "with_hc_in_upgrade")
    def test_constraint_removed(self, cluster_with_component):
        """Test constraint is removed in new bundle version"""
        cluster, component = cluster_with_component
        host = cluster.host()
        upgrade = cluster.upgrade()
        task = expect_no_api_error(
            'upgrade cluster with "broken" constraint (for current proto)',
            upgrade.do,
            hc=build_hc_for_hc_acl_action(cluster, remove=[(component, host)]),
        )
        wait_for_task_and_assert_result(task, "success", action_name=upgrade.name)

    # pylint: disable-next=too-many-locals
    def test_upgrade_with_hc_acl_new_component_with_constraint(self, cluster_with_new_component, generic_provider):
        """Test upgrade when new component appears and it has constraints"""
        upgrade_name = "with_hc_acl"
        message = "Host-component map of upgraded cluster should satisfy constraints of new bundle. Now error is:"
        cluster, service, component = cluster_with_new_component
        cluster_proto_id, service_proto_id, component_proto_id = (
            cluster.prototype_id,
            service.prototype_id,
            component.prototype_id,
        )
        with allure.step("Map component on 1 host"):
            cluster.hostcomponent_set((cluster.host_add(generic_provider.host_create("host-1")), component))
        with allure.step(f"Run upgrade {upgrade_name} and expect it to fail"):
            hc_kwargs = {"hc": build_hc_for_hc_acl_action(cluster)} if upgrade_name.startswith("with_") else {}
            task = cluster.upgrade(name=upgrade_name).do(**hc_kwargs)
            wait_for_task_and_assert_result(task, "failed", action_name=upgrade_name)
            _ = cluster.reread() or service.reread() or component.reread()
        with allure.step("Check that correct job failed and it has a message about broken constraints"):
            failed_job = task.job(status="failed")
            assert (
                failed_job.display_name == "switch"
            ), f'Wrong job failed, expected bundle switch job to be failed, not "{failed_job.display_name}"'
            log = failed_job.log(type="stderr")
            assert message in log.content, (
                f'No incorrect constraints message found in "stderr" of failed bundle switch.'
                f"\nExpected: {message}\nActual: {log.content}"
            )
        with allure.step("Check that upgrade is reverted"):
            self._check_hc_stays_the_same_after_upgrade(cluster)
            assert (
                cluster.prototype_id == cluster_proto_id
            ), "Cluster prototype should not be changed after failed upgrade"
            assert (
                service.prototype_id == service_proto_id
            ), "Service prototype should not be changed after failed upgrade"
            assert (
                component.prototype_id == component_proto_id
            ), "Component prototype should not be changed after failed upgrade"

    def test_upgrade_without_hc_acl_new_component_with_constraint(self, cluster_with_new_component, generic_provider):
        """Test upgrade when new component appears, and it has constraints, but no hc_acl in upgrade definition"""
        upgrade_name = "without_hc_acl"
        cluster, service, component = cluster_with_new_component
        with allure.step("Map component on 1 host"):
            cluster.hostcomponent_set((cluster.host_add(generic_provider.host_create("host-1")), component))
        with allure.step(f"Run upgrade {upgrade_name} and expect it to succeed"):
            task = cluster.upgrade(name=upgrade_name).do()
            wait_for_task_and_assert_result(task, "success", action_name=upgrade_name)
            _ = cluster.reread() or service.reread() or component.reread()
        with allure.step("Check that state after upgrade is correct"):
            self._check_hc_stays_the_same_after_upgrade(cluster)
            assert len(cluster.concerns()) == 1, "There should be exactly 1 concern on cluster after an upgrade"

    @allure.step("Check HC is the same as it was before the upgrade")
    def _check_hc_stays_the_same_after_upgrade(self, cluster):
        hostcomponent = cluster.hostcomponent()
        assert len(hostcomponent) == 1, f"Only one entry should be in HC map: {hostcomponent}"
        assert all(
            hostcomponent[0][id_key] for id_key in ("host_id", "service_id", "component_id")
        ), f"Host, service and component id should be 1 in HC entry. Actual HC: {hostcomponent}"
