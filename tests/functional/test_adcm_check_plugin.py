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

"""Tests for ADCM ansible plugins"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Host
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result
from adcm_pytest_plugin.steps.asserts import assert_action_result
from tests.library.consts import MessageStates, States

NO_FIELD = [
    "no_title",
    "no_result",
    "no_msg",
    "only_success",
    "only_fail",
    "bad_result",
]


@pytest.mark.parametrize("missed_field", NO_FIELD)
def test_field_validation(sdk_client_fs: ADCMClient, missed_field):
    """Check bad configurations: missed title,
    missed result field, missed message field,
    only success message field, only fail message field.
    Expected result: job failed.
    """
    params = {"action": "adcm_check", "expected_state": States.failed, "logs_amount": 2}
    bundle_dir = utils.get_data_dir(__file__, missed_field)
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name=params["action"]).run()
    task.wait()
    assert_action_result(result=task.status, status=params["expected_state"], name=params["action"])
    with allure.step(f'Check if logs count is equal {params["logs_amount"]}'):
        job = task.job()
        logs = job.log_list()
        current_len = len(logs)
        assert (
            current_len == params["logs_amount"]
        ), f'Logs count not equal {params["logs_amount"]}, current log count {current_len}'


@pytest.mark.parametrize(
    ("name", "result"),
    [
        ("all_fields", ("Group success", "Task success", True, True)),
        ("all_fields_fail", ("Group fail", "Task fail", False, False)),
    ],
)
def test_all_fields(sdk_client_fs: ADCMClient, name, result):
    """Check that we can run jobs with all fields for
    adcm_check task and check all fields after action
    execution.
    """
    group_msg, task_msg, group_result, task_result = result
    params = {
        "action": "adcm_check",
        "expected_state": States.success,
        "expected_title": "Name of group check.",
        "content_title": "Check",
    }
    cluster = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, name)).cluster_create(utils.random_string())
    task = run_cluster_action_and_assert_result(cluster, action=params["action"], status=params["expected_state"])
    job = task.job()
    with allure.step("Check all fields after action execution"):
        content = job.log_list()[2].content[0]
        assert content["message"] == group_msg, f'Expected message {group_msg}. Current message {content["message"]}'
        assert content["result"] is group_result
        assert (
            content["title"] == params["expected_title"]
        ), f'Expected title {params["expected_title"]}. Current title {content["title"]}'
        content_title = content["content"][0]["title"]
        assert (
            content_title == params["content_title"]
        ), f'Expected title {params["content_title"]}. Current title {content_title}'
        content_message = content["content"][0]["message"]
        assert content_message == task_msg, f"Expected message {task_msg}. Current message {content_message}"
        assert content["content"][0]["result"] is task_result


@pytest.mark.parametrize(
    "name",
    ["with_success", "with_fail", "with_success_msg_on_fail", "with_fail_msg_on_fail"],
)
def test_message_with_other_field(sdk_client_fs: ADCMClient, name):
    """Check that we can create action with
    specific (success or fail) message and message.
    Expected that missed message will be written in
    msg attribute and specific message
    will be in success or fail attribute depends on config.
    """
    params = {
        "action": "adcm_check",
        "expected_state": States.success,
    }
    bundle_dir = utils.get_data_dir(__file__, name)
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name=params["action"]).run()
    task.wait()
    job = task.job()
    assert_action_result(result=job.status, status=params["expected_state"], name=params["action"])
    with allure.step(f"Check if content message is {name}"):
        log = job.log_list()[2]
        content = log.content[0]
        assert content["message"] == name, f'Expected content message {name}. Current {content["message"]}'


def test_success_and_fail_msg_on_success(sdk_client_fs: ADCMClient):
    """Check that we can run adcm_check plugin with success and fail message and
    success and fail message will be in their own fields.
    """
    params = {
        "action": "adcm_check",
        "expected_state": States.success,
        "expected_message": MessageStates.success_msg,
    }
    bundle_dir = utils.get_data_dir(__file__, "success_and_fail_msg")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name=params["action"]).run()
    task.wait()
    job = task.job()
    assert_action_result(result=job.status, status=params["expected_state"], name=params["action"])
    with allure.step("Check if success and fail message are in their own fields."):
        log = job.log_list()[2]
        content = log.content[0]
        assert content["result"], f'Result is {content["result"]} expected True'
        assert content["message"] == params["expected_message"], (
            f'Expected message: {params["expected_message"]}. ' f'Current message {content["message"]}'
        )


def test_success_and_fail_msg_on_fail(sdk_client_fs: ADCMClient):
    """Check that we can run adcm_check plugin with success and fail message and
    success and fail message will be in their own fields.
    """
    params = {
        "action": "adcm_check",
        "expected_state": States.success,
        "expected_message": MessageStates.fail_msg,
    }
    bundle_dir = utils.get_data_dir(__file__, "success_and_fail_msg_on_fail")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name=params["action"]).run()
    task.wait()
    job = task.job()
    assert_action_result(result=job.status, status=params["expected_state"], name=params["action"])
    with allure.step("Check if success and fail message are in their own fields"):
        log = job.log_list()[2]
        content = log.content[0]
        assert not content["result"], f'Result is {content["result"]} expected True'
        assert content["message"] == params["expected_message"], (
            f'Expected message: {params["expected_message"]}. ' f'Current message {content["message"]}'
        )


def test_multiple_tasks(sdk_client_fs: ADCMClient):
    """Check adcm_check with multiple tasks with different parameters."""
    params = {
        "action": "check_sample",
        "logs_amount": 3,
    }
    expected_result = [
        ('"This is message. Params: msg. result=yes"', "Check log 1", True),
        (
            "This is fail message. Params: success_msg, fail_msg. result=no",
            "Check log 2",
            False,
        ),
        (
            "This is success message. Params: success_msg, fail_msg. result=yes",
            "Check log 3",
            True,
        ),
    ]
    bundle_dir = utils.get_data_dir(__file__, "multiple_tasks")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    action = cluster.action(name=params["action"]).run()
    action.wait()
    with allure.step(f'Check if log content is equal {params["logs_amount"]}'):
        job = action.job()
        log = job.log_list()[2]
        assert len(log.content) == params["logs_amount"], log.content
    with allure.step("Check log's messages, titles and results."):
        for result in expected_result:
            log_entry = log.content[expected_result.index(result)]
            assert (
                result[0] == log_entry["message"]
            ), f"Expected message {result[0]}. Actual message {log_entry['message']}"
            assert result[1] == log_entry["title"], f"Expected title {result[1]}. Actual title {log_entry['title']}"
            assert result[2] is log_entry["result"], f"Expected result {result[2]}. Actual result {log_entry['result']}"


def test_multiple_group_tasks(sdk_client_fs: ADCMClient):
    """Check that we have correct field values for group tasks"""
    expected_result_groups = [
        ("This is fail message", "Group 1", False),
        ("", "Group 2", True),
    ]
    group1_expected = [
        (
            "Check log 1",
            "This is message. Params: group_title, group_success_msg, group_fail_msg, msg. result=yes",
            True,
        ),
        (
            "Check log 2",
            "This is message. Params: group_title, group_success_msg, group_fail_msg, msg. result=no",
            False,
        ),
    ]
    group2_expected = [
        (
            "Check log 3",
            "This is success message. Params: group_title, success_msg, fail_msg. result=yes",
            True,
        )
    ]
    bundle_dir = utils.get_data_dir(__file__, "multiple_tasks_groups")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    action = cluster.action(name="check_sample").run()
    action.wait()
    with allure.step("Check log content amount"):
        job = action.job()
        log = job.log_list()[2]
        assert len(log.content) == 2, log.content
        assert len(log.content[0]["content"]) == 2, log.content[0].content
        assert len(log.content[1]["content"]) == 1, log.content[1].content
    with allure.step("Check log's messages, titles and results."):
        for result in expected_result_groups:
            log_entry = log.content[expected_result_groups.index(result)]
            assert (
                result[0] == log_entry["message"]
            ), f"Expected message {result[0]}. Actual message {log_entry['message']}"
            assert result[1] == log_entry["title"], f"Expected title {result[1]}. Actual title {log_entry['title']}"
            assert result[2] is log_entry["result"], f"Expected result {result[2]}. Actual result {log_entry['result']}"
    with allure.step("Check group content"):
        group1 = log.content[0]["content"]
        group2 = log.content[1]
        for result in group1_expected:
            log_entry = group1[group1_expected.index(result)]
            assert result[0] == log_entry["title"], f"Expected title {result[0]}. Actual message {log_entry['title']}"
            assert (
                result[1] == log_entry["message"]
            ), f"Expected message {result[1]}. Actual message {log_entry['message']}"
            assert result[2] is log_entry["result"], f"Expected result {result[2]}. Actual result {log_entry['result']}"
        for result in group2_expected:
            log_entry = group2["content"][group2_expected.index(result)]
            assert result[0] == log_entry["title"], f"Expected title {result[0]}. Actual message {log_entry['title']}"
            assert (
                result[1] == log_entry["message"]
            ), f"Expected message {result[1]}. Actual message {log_entry['message']}"
            assert result[2] is log_entry["result"], f"Expected result {result[2]}. Actual result {log_entry['result']}"


def test_multiple_group_tasks_without_group_title(sdk_client_fs: ADCMClient):
    """Check group task without title."""
    params = {
        "action": "check_sample",
        "logs_amount": 2,
    }
    bundle_dir = utils.get_data_dir(__file__, "group_tasks_without_group_title")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    action = cluster.action(name=params["action"]).run()
    action.wait()
    with allure.step(f'Check log content amount is equal {params["logs_amount"]}'):
        job = action.job()
        log = job.log_list()[2]
        assert len(log.content) == params["logs_amount"], log.content
    with allure.step("Check title and result in log content"):
        for log_entry in log.content:
            assert (
                log_entry["title"] == "Check log 1"
            ), f"Expected title 'Check log 1'. Current title {log_entry['title']}"
            assert log_entry["result"], "Result is False, Expected True"


def test_multiple_tasks_action_with_log_files_check(sdk_client_fs: ADCMClient):
    """Check that log_files parameter don't affect action"""
    params = {
        "action": "check_sample",
        "expected_state": States.success,
    }

    bundle_dir = utils.get_data_dir(__file__, "log_files_check")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name=params["action"]).run()
    task.wait()
    job = task.job()
    assert_action_result(result=job.status, status=params["expected_state"], name=params["action"])
    with allure.step("Check if result is True"):
        log = job.log_list()[2]
        content = log.content[0]
        assert content["result"], f'Result is {content["result"]}, Expected True'


def test_result_no(sdk_client_fs: ADCMClient):
    """Check config with result no"""
    params = {
        "action": "adcm_check",
        "expected_state": States.success,
    }
    bundle_dir = utils.get_data_dir(__file__, "result_no")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name=params["action"]).run()
    task.wait()
    job = task.job()
    assert_action_result(result=job.status, status=params["expected_state"], name=params["action"])
    with allure.step("Check if result is False"):
        log = job.log_list()[2]
        content = log.content[0]
        assert not content["result"], f'Result is {content["result"]}, Expected False'


class TestDatabaseIsMalformed:
    """Test call to adcm_check from many hosts doesn't cause "database is malformed" error"""

    @pytest.fixture()
    def cluster(self, sdk_client_fs) -> Cluster:
        """Create cluster"""
        bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "parallel", "cluster"))
        return bundle.cluster_create("Test Cluster")

    @pytest.fixture()
    def hosts(self, sdk_client_fs, cluster) -> [Host]:
        """Create and return 50 hosts bonded to a cluster"""
        bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "parallel", "provider"))
        provider = bundle.provider_create("Test Provider")
        return [cluster.host_add(provider.host_create(fqdn=f"test-host-{i}")) for i in range(50)]

    @allure.issue(name="Database is malformed", url="https://arenadata.atlassian.net/browse/ADCM-2169")
    @pytest.mark.full()
    @pytest.mark.usefixtures("hosts")
    def test_multiple_parallel_check_run(self, cluster):
        """
        Run cluster action adcm_check change on 50 hosts
        """
        for _ in range(5):
            run_cluster_action_and_assert_result(cluster, "check")
