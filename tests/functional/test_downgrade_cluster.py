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
from functools import partial

import allure
import pytest
from adcm_client.objects import Bundle, Cluster, Component, Service
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_service_action_and_assert_result,
    wait_for_task_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir
from coreapi.exceptions import ErrorMessage

from tests.functional.tools import compare_object_multi_state, compare_object_state
from tests.library.assertions import dicts_are_equal, expect_no_api_error

# pylint: disable=redefined-outer-name


DEFAULT_CONFIG = {
    "string": None,
    "map": {"age": "24", "sex": "m", "name": "Joe"},
    "list": ["/dev/rdisk0s1", "/dev/rdisk0s2", "/dev/rdisk0s3"],
    "float": 1.0,
    "option": "DAILY",
    "boolean": True,
    "integer": 16,
    "structure": [
        {"code": 30, "country": "Greece"},
        {"code": 33, "country": "France"},
        {"code": 34, "country": "Spain"},
    ],
}
EMPTY_CONFIG = {"string": None}
CHANGED_DEFAULT_CONFIG = {
    "string": "string",
    "map": {"age": "25", "sex": "m", "name": "John"},
    "list": ["/dev/rdisk0s4", "/dev/rdisk0s5", "/dev/rdisk0s6"],
    "float": 3.0,
    "option": "WEEKLY",
    "boolean": False,
    "integer": 17,
    "structure": [
        {"code": 20, "country": "Canada"},
        {"code": 23, "country": "Australia"},
        {"code": 24, "country": "China"},
    ],
}
CHANGED_EMPTY_CONFIG = {"string": "string", "boolean": False, "float": 1.0}
expect_default_config = partial(
    dicts_are_equal, expected=DEFAULT_CONFIG, message="Config isn't correct.\nCheck attachments for more details."
)
expect_empty_config = partial(
    dicts_are_equal, expected=EMPTY_CONFIG, message="Config isn't correct.\nCheck attachments for more details."
)
expect_changed_default_config = partial(
    dicts_are_equal,
    expected=CHANGED_DEFAULT_CONFIG,
    message="Config isn't correct.\nCheck attachments for more details.",
)
expect_changed_empty_config = partial(
    dicts_are_equal, expected=CHANGED_EMPTY_CONFIG, message="Config isn't correct.\nCheck attachments for more details."
)


@pytest.fixture()
def old_bundle(sdk_client_fs) -> Bundle:
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "downgrade_cluster_1"))


@pytest.fixture()
def old_bundle_full(sdk_client_fs) -> Bundle:
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "downgrade_full_cluster_1"))


@pytest.fixture()
def old_bundle_multistate(sdk_client_fs) -> Bundle:
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "downgrade_multistate_cluster_1"))


@pytest.fixture()
def old_bundle_change_multistate(sdk_client_fs) -> Bundle:
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "downgrade_multistate_change_cluster_1"))


class MultiState:
    FAILED = "multi_fail_on_last"
    SUCCESS = "multi_ok"


@allure.step("Run action on adcm objects")
def _run_action_on_cluster_objects(
    cluster: Cluster, service: Service, component: Component, action: str, status: str
) -> None:
    run_cluster_action_and_assert_result(cluster, action, status=status)
    run_service_action_and_assert_result(service, action, status=status)
    run_component_action_and_assert_result(component, action, status=status)


@allure.step("Check state and multistate on cluster objects")
def _check_states_on_cluster_objects(
    cluster: Cluster, service: Service, component: Component, expected_state: str, expected_multistate: list
) -> None:
    compare_object_state(adcm_object=cluster, expected_state=expected_state)
    compare_object_multi_state(adcm_object=cluster, expected_state=expected_multistate)

    compare_object_state(adcm_object=service, expected_state=expected_state)
    compare_object_multi_state(adcm_object=service, expected_state=expected_multistate)

    compare_object_state(adcm_object=component, expected_state=expected_state)
    compare_object_multi_state(adcm_object=component, expected_state=expected_multistate)


@allure.step("Try to delete service")
def _service_can_be_removed(service: Service) -> bool:
    try:
        service.delete()
        return True
    except ErrorMessage as e:
        if hasattr(e.error, "title") and e.error.title == "409 Conflict":
            return False
        raise AttributeError(f"Wrong error message. Expected error with title: '409 Conflict'\nActual is: {e}") from e


def test_revert_simple_config(sdk_client_fs, old_bundle):
    """Test to check how revert upgrade work with simple config with requirements"""
    with allure.step("Create clusters and services"):
        cluster = old_bundle.cluster_create("downgrade_cluster")

        first_service = cluster.service_add(name="service1")
        first_component = first_service.component(name="component11")
        second_service = cluster.service_add(name="service2")
        second_component = second_service.component(name="component21")

        cluster_objects_before_upgrade_full_config = [cluster, first_service, second_component]
        cluster_objects_before_upgrade_lite_config = [first_component, second_service]

    with allure.step("Check cluster state and config"):
        compare_object_state(adcm_object=cluster, expected_state="created")

        for obj in cluster_objects_before_upgrade_full_config:
            expect_default_config(actual=obj.config())
        for obj in cluster_objects_before_upgrade_lite_config:
            expect_empty_config(actual=obj.config())

    with allure.step("Run action install and check state and config"):
        task_status = cluster.action(name="install").run().wait()
        assert task_status == "success"
        compare_object_state(adcm_object=cluster, expected_state="install")

        for obj in cluster_objects_before_upgrade_full_config:
            expect_default_config(actual=obj.config())
        for obj in cluster_objects_before_upgrade_lite_config:
            expect_empty_config(actual=obj.config())

    with allure.step("Upgrade cluster and check state and config"):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "downgrade_cluster_2"))
        upgrade = cluster.upgrade(name="switch_bundle_upgrade")
        task = expect_no_api_error("upgrade cluster", upgrade.do)
        wait_for_task_and_assert_result(task, "success", action_name=upgrade.name)
        compare_object_state(adcm_object=cluster, expected_state="upgrading")

        for obj in [cluster, first_service, first_component]:
            expect_changed_empty_config(actual=obj.config())
        for obj in [second_component, second_service]:
            expect_changed_default_config(actual=obj.config())

        config = {"string": "hoho"}
        cluster.config_set_diff(config)

    with allure.step("Revert upgrade and check state and config"):
        task_status = cluster.action(name="revert_upgrade").run().wait()
        assert task_status == "success"
        compare_object_state(adcm_object=cluster, expected_state="install")

        for obj in cluster_objects_before_upgrade_full_config:
            expect_default_config(actual=obj.config())
        for obj in cluster_objects_before_upgrade_lite_config:
            expect_empty_config(actual=obj.config())


def test_revert_config_secrets(sdk_client_fs, old_bundle_full):
    """Test to check how revert upgrade work with secrets in config"""
    with allure.step("Create clusters and services"):
        cluster = old_bundle_full.cluster_create("downgrade_cluster_full")

        first_service = cluster.service_add(name="service1")
        first_component = first_service.component(name="component11")

    with allure.step("Check cluster state and config"):
        compare_object_state(adcm_object=cluster, expected_state="created")
        _run_action_on_cluster_objects(
            cluster=cluster, service=first_service, component=first_component, action="check_after_1", status="success"
        )

    with allure.step("Run action install and check state and config"):
        run_cluster_action_and_assert_result(cluster, "install")

        compare_object_state(adcm_object=cluster, expected_state="install")
        _run_action_on_cluster_objects(
            cluster=cluster, service=first_service, component=first_component, action="check_after_1", status="success"
        )

    with allure.step("Upgrade cluster and check state and config"):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "downgrade_full_cluster_2"))
        upgrade = cluster.upgrade(name="switch_bundle_upgrade")
        task = expect_no_api_error("upgrade cluster", upgrade.do)
        wait_for_task_and_assert_result(task, "success", action_name=upgrade.name)

        compare_object_state(adcm_object=cluster, expected_state="upgrading")
        _run_action_on_cluster_objects(
            cluster=cluster, service=first_service, component=first_component, action="check_after_2", status="success"
        )

    with allure.step("Revert upgrade and check state and config"):
        run_cluster_action_and_assert_result(cluster, "revert_upgrade")
        compare_object_state(adcm_object=cluster, expected_state="install")
        _run_action_on_cluster_objects(
            cluster=cluster, service=first_service, component=first_component, action="check_after_1", status="success"
        )


def test_revert_config_multistate_does_not_change(sdk_client_fs, old_bundle_multistate):
    """Test to check multi-state does not change after revert"""
    cluster = old_bundle_multistate.cluster_create("multistate_cluster")
    first_service = cluster.service_add(name="service1")
    first_component = first_service.component(name="component11")

    with allure.step("Run set_multistate action"):
        _run_action_on_cluster_objects(
            cluster=cluster, service=first_service, component=first_component, action="set_multistate", status="success"
        )

    with allure.step("Run success action"):
        run_cluster_action_and_assert_result(cluster, "state_changing_success", status="success")
        compare_object_state(adcm_object=cluster, expected_state="multi_ok")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.SUCCESS])

    with allure.step("Run failed action"):
        run_cluster_action_and_assert_result(cluster, "state_changing_fail", status="failed")
        compare_object_state(adcm_object=cluster, expected_state="not_multi_state")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED, MultiState.SUCCESS])

    with allure.step("Upgrade cluster"):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "downgrade_multistate_cluster_2"))
        upgrade = cluster.upgrade(name="switch_bundle_upgrade")
        task = expect_no_api_error("upgrade cluster", upgrade.do)
        wait_for_task_and_assert_result(task, "success", action_name=upgrade.name)

        compare_object_state(adcm_object=cluster, expected_state="upgrading")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED, MultiState.SUCCESS])

    with allure.step("Remove old cluster service"):
        assert not _service_can_be_removed(
            service=first_service
        ), f"Service {first_service.name} shouldn't be allowed to be deleted"

    with allure.step("Add and remove new service"):
        cluster.reread()
        service_to_delete = cluster.service_add(name="service_from_update")
        assert _service_can_be_removed(
            service=service_to_delete
        ), f"Service {service_to_delete.name} should be allowed to be deleted"

    with allure.step("Run failed action"):
        run_cluster_action_and_assert_result(cluster, "state_changing_fail", status="failed")
        compare_object_state(adcm_object=cluster, expected_state="not_multi_state")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED, MultiState.SUCCESS])

    with allure.step("Run success action"):
        run_cluster_action_and_assert_result(cluster, "state_changing_success", status="success")
        compare_object_state(adcm_object=cluster, expected_state="multi_ok")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED, MultiState.SUCCESS])

    with allure.step("Revert upgrade"):
        task_status = cluster.action(name="revert_upgrade").run().wait()
        assert task_status == "success"

        compare_object_state(adcm_object=cluster, expected_state="not_multi_state")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED, MultiState.SUCCESS])

    with allure.step("Run success action"):
        run_cluster_action_and_assert_result(cluster, "second_state_changing_success", status="success")
        compare_object_state(adcm_object=cluster, expected_state="multi_ok")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED, MultiState.SUCCESS])

    with allure.step("Upgrade cluster"):
        upgrade = cluster.upgrade(name="switch_bundle_upgrade")
        task = expect_no_api_error("upgrade cluster", upgrade.do)
        wait_for_task_and_assert_result(task, "success", action_name=upgrade.name)

        compare_object_state(adcm_object=cluster, expected_state="upgrading")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED, MultiState.SUCCESS])


def test_revert_config_multistate_change(sdk_client_fs, old_bundle_change_multistate):
    """Test to check multi-state does not change after revert"""
    cluster = old_bundle_change_multistate.cluster_create("multistate_cluster_change")
    first_service = cluster.service_add(name="service1")
    first_component = first_service.component(name="component11")

    _run_action_on_cluster_objects(
        cluster=cluster, service=first_service, component=first_component, action="set_multistate", status="success"
    )

    with allure.step("Run failed action"):
        run_cluster_action_and_assert_result(cluster, "state_changing_fail", status="failed")
        compare_object_state(adcm_object=cluster, expected_state="not_multi_state")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED])

    with allure.step("Upgrade cluster"):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "downgrade_multistate_change_cluster_2"))
        upgrade = cluster.upgrade(name="switch_bundle_upgrade")
        task = expect_no_api_error("upgrade cluster", upgrade.do)
        wait_for_task_and_assert_result(task, "success", action_name=upgrade.name)

        compare_object_state(adcm_object=cluster, expected_state="upgrading")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED])

    with allure.step("Run success action"):
        run_cluster_action_and_assert_result(cluster, "state_changing_success", status="success")
        compare_object_state(adcm_object=cluster, expected_state="multi_ok")
        compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED, MultiState.SUCCESS])

    with allure.step("Revert upgrade"):
        task_status = cluster.action(name="revert_upgrade").run().wait()
        assert task_status == "success"

        compare_object_state(adcm_object=cluster, expected_state="reverting")
        compare_object_multi_state(adcm_object=cluster, expected_state=["changed_success", MultiState.SUCCESS])


@pytest.mark.parametrize("action_name", ["state_changing_fail", "state_changing_success"])
def test_revert_config_multi_state(sdk_client_fs, old_bundle_multistate, action_name):
    """Test to check how revert upgrade work with multistate"""
    cluster = old_bundle_multistate.cluster_create("multistate_cluster")
    first_service = cluster.service_add(name="service1")
    first_component = first_service.component(name="component11")

    expected_object_state = "not_multi_state" if action_name == "state_changing_fail" else "multi_ok"
    expected_object_multi_state = [MultiState.FAILED if action_name == "state_changing_fail" else MultiState.SUCCESS]
    expected_action_status = "failed" if action_name == "state_changing_fail" else "success"
    expected_updated_multi_state = (
        [MultiState.FAILED, MultiState.SUCCESS] if action_name == "state_changing_fail" else [MultiState.SUCCESS]
    )

    _run_action_on_cluster_objects(
        cluster=cluster, service=first_service, component=first_component, action="set_multistate", status="success"
    )
    with allure.step("Run action"):
        _run_action_on_cluster_objects(
            cluster=cluster,
            service=first_service,
            component=first_component,
            action=action_name,
            status=expected_action_status,
        )
        _check_states_on_cluster_objects(
            cluster=cluster,
            service=first_service,
            component=first_component,
            expected_state=expected_object_state,
            expected_multistate=expected_object_multi_state,
        )

    with allure.step("Upgrade cluster"):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "downgrade_multistate_cluster_2"))
        upgrade = cluster.upgrade(name="switch_bundle_upgrade")
        task = expect_no_api_error("upgrade cluster", upgrade.do)
        wait_for_task_and_assert_result(task, "success", action_name=upgrade.name)

    with allure.step("Check state"):
        compare_object_state(adcm_object=cluster, expected_state="upgrading")
        compare_object_multi_state(adcm_object=cluster, expected_state=expected_object_multi_state)
        assert "revert_upgrade" not in [i.display_name for i in cluster.action_list()]

        compare_object_state(adcm_object=first_service, expected_state=expected_object_state)
        compare_object_multi_state(adcm_object=first_service, expected_state=expected_object_multi_state)
        assert "revert_upgrade" not in [i.display_name for i in first_service.action_list()]

        compare_object_state(adcm_object=first_component, expected_state=expected_object_state)
        compare_object_multi_state(adcm_object=first_component, expected_state=expected_object_multi_state)
        assert "revert_upgrade" not in [i.display_name for i in first_component.action_list()]

    with allure.step("Run success action"):
        _run_action_on_cluster_objects(
            cluster=cluster,
            service=first_service,
            component=first_component,
            action="state_changing_success",
            status="success",
        )
        compare_object_state(adcm_object=first_service, expected_state="multi_ok")
        compare_object_multi_state(adcm_object=first_service, expected_state=expected_updated_multi_state)

    with allure.step("Revert upgrade"):
        task_status = cluster.action(name="revert_upgrade").run().wait()
        assert task_status == "success"

    with allure.step("Check state after revert"):
        _check_states_on_cluster_objects(
            cluster=cluster,
            service=first_service,
            component=first_component,
            expected_state=expected_object_state,
            expected_multistate=expected_updated_multi_state,
        )
