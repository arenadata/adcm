# pylint: disable=W0611, W0621
import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils

NO_FIELD = ['no_title', 'no_result', 'no_msg', 'only_success', 'only_fail', 'bad_result']
ALL_FIELDS_DATA = [("all_fields", "Group success", "Task success", True, True),
                   ("all_fields_fail", "Group fail", "Task fail", False, False)]


@pytest.mark.parametrize("missed_field", NO_FIELD)
def test_field_validation(sdk_client_fs: ADCMClient, missed_field):
    """Check bad configurations: missed title, missed result field, missed message field,
    only success message field, only fail message field. Expected result: job failed.
    """
    bundle_dir = utils.get_data_dir(__file__, missed_field)
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action_run(name='adcm_check')
    task.wait()
    with allure.step('Check if job status is failed, action name: adcm_check'):
        assert task.status == 'failed', \
            "Current job status {}. Expected: failed".format(task.status)
    with allure.step('Check if logs count not equal 2'):
        job = task.job()
        logs = job.log_list()
        assert len(logs) == 2, "Logs count not equal 2, current log count {}".format(len(logs))


@pytest.mark.parametrize("name, group_msg, task_msg, group_result, task_result", ALL_FIELDS_DATA)
def test_all_fields(sdk_client_fs: ADCMClient, name, group_msg,
                    task_msg, group_result, task_result):
    """Check that we can run jobs with all fields for
     adcm_check task and check all fields after action
    execution.
    """
    bundle_dir = utils.get_data_dir(__file__, name)
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action_run(name='adcm_check')
    task.wait()
    with allure.step('Check if job status is success, action name: adcm_check'):
        job = task.job()
        assert job.status == 'success', \
            "Current job status {}. Expected: success".format(job.status)
    with allure.step('Check all fields after action execution'):
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[2].id)
        content = log.content[0]
        assert content['message'] == group_msg,\
            "Expected message {}. Current message {}".format(group_msg, content['message'])
        assert content['result'] is group_result
        assert content['title'] == 'Name of group check.',\
            "Expected title 'Name of group check'. Current title {}".format(content['title'])
        assert content['content'][0]['title'] == 'Check',\
            'Current title {}. Expected title: Check'.format(content[0]['title'])
        assert content['content'][0]['message'] == task_msg,\
            "Expected message {}. Current message {}".format(task_msg, content[0]['message'])
        assert content['content'][0]['result'] is task_result


@pytest.mark.parametrize("name", ['with_success', 'with_fail',
                                  'with_success_msg_on_fail', 'with_fail_msg_on_fail'])
def test_message_with_other_field(sdk_client_fs: ADCMClient, name):
    """Check that we can create action with specific (success or fail) message and message.
    Expected that missed message will be written in msg attribute and specific message
    will be in success or fail attribute depends on config.
    """
    bundle_dir = utils.get_data_dir(__file__, name)
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action_run(name='adcm_check')
    task.wait()
    with allure.step('Check if job status is success, action name: adcm_check'):
        job = task.job()
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[2].id)
        assert job.status == 'success', \
            "Current job status {}. Expected: success".format(job.status)
    with allure.step('Check if content message is {}'.format(name)):
        content = log.content[0]
        assert content['message'] == name,\
            "Expected content message {}. Current {}".format(name, content['message'])


def test_success_and_fail_msg_on_success(sdk_client_fs: ADCMClient):
    """Check that we can run adcm_check plugin with success and fail message and
    success and fail message will be in their own fields.
    """
    bundle_dir = utils.get_data_dir(__file__, 'success_and_fail_msg')
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action_run(name='adcm_check')
    task.wait()
    with allure.step('Check if job status is success, action name: adcm_check'):
        job = task.job()
        assert job.status == 'success', \
            "Current job status {}. Expected: success".format(job.status)
    with allure.step('Check if success and fail message are in their own fields.'):
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[2].id)
        content = log.content[0]
        assert content['result'], "Result is False expected True"
        assert content['message'] == 'success_msg',\
            "Expected message: 'success_msg. Current message {}".format(content['message'])


def test_success_and_fail_msg_on_fail(sdk_client_fs: ADCMClient):
    """Check that we can run adcm_check plugin with success and fail message and
    success and fail message will be in their own fields.
    """
    bundle_dir = utils.get_data_dir(__file__, 'success_and_fail_msg_on_fail')
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action_run(name='adcm_check')
    task.wait()
    with allure.step('Check if job status is success, action name: adcm_check'):
        job = task.job()
        assert job.status == 'success', \
            "Current job status {}. Expected: success".format(job.status)
    with allure.step('Check if success and fail message are in their own fields.'):
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[2].id)
        content = log.content[0]
        assert not content['result'], "Result is False expected True"
        assert content['message'] == 'fail_msg',\
            "Expected message: 'fail_msg. Current message {}".format(content['message'])


def test_multiple_tasks(sdk_client_fs: ADCMClient):
    """Check adcm_check with multiple tasks with different parameters.
    """
    expected_result = [('"This is message. Params: msg. result=yes"',
                        'Check log 1', True),
                       ("This is fail message. Params: success_msg, fail_msg. result=no",
                        "Check log 2", False),
                       ("This is success message. Params: success_msg, fail_msg. result=yes",
                        "Check log 3", True),
                       ]
    bundle_dir = utils.get_data_dir(__file__, 'multiple_tasks')
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    action = cluster.action_run(name='check_sample')
    action.wait()
    with allure.step('Check if log content is equal 3.'):
        job = action.job()
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[2].id)
        assert len(log.content) == 3, log.content
    with allure.step("Check log's messages, titles and results."):
        for result in expected_result:
            log_entry = log.content[expected_result.index(result)]
            assert result[0] == log_entry['message'],\
                "Expected message {}. Actual message {}".format(result[0], log_entry['message'])
            assert result[1] == log_entry['title'], \
                "Expected title {}. Actual title {}".format(result[1], log_entry['title'])
            assert result[2] is log_entry['result'], \
                "Expected result {}. Actual result {}".format(result[2], log_entry['result'])


def test_multiple_group_tasks(sdk_client_fs: ADCMClient):
    """Check that we have correct field values for group tasks
    """
    expected_result_groups = [("This is fail message",
                               "Group 1", False),
                              ("", "Group 2", True)]
    group1_expected = [("Check log 1",
                        "This is message. Params: group_title,"
                        " group_success_msg, group_fail_msg, msg. result=yes",
                        True),
                       ("Check log 2",
                        "This is message. Params: group_title,"
                        " group_success_msg, group_fail_msg, msg. result=no",
                        False)]
    group2_expected = [("Check log 3",
                        "This is success message."
                        " Params: group_title, success_msg, fail_msg. result=yes",
                        True)]
    bundle_dir = utils.get_data_dir(__file__, 'multiple_tasks_groups')
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    action = cluster.action_run(name='check_sample')
    action.wait()
    with allure.step('Check log content amount'):
        job = action.job()
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[2].id)
        assert len(log.content) == 2, log.content
        assert len(log.content[0]['content']) == 2, log.content[0].content
        assert len(log.content[1]['content']) == 1, log.content[1].content
    with allure.step("Check log's messages, titles and results."):
        for result in expected_result_groups:
            log_entry = log.content[expected_result_groups.index(result)]
            assert result[0] == log_entry['message'], \
                "Expected message {}. Actual message {}".format(result[0], log_entry['message'])
            assert result[1] == log_entry['title'], \
                "Expected title {}. Actual title {}".format(result[1], log_entry['title'])
            assert result[2] is log_entry['result'], \
                "Expected result {}. Actual result {}".format(result[2], log_entry['result'])
    with allure.step('Check group content'):
        group1 = log.content[0]['content']
        group2 = log.content[1]
        for result in group1_expected:
            log_entry = group1[group1_expected.index(result)]
            assert result[0] == log_entry['title'],  \
                "Expected title {}. Actual message {}".format(result[0], log_entry['title'])
            assert result[1] == log_entry['message'], \
                "Expected message {}. Actual message {}".format(result[1], log_entry['message'])
            assert result[2] is log_entry['result'],  \
                "Expected result {}. Actual result {}".format(result[2], log_entry['result'])
        for result in group2_expected:
            log_entry = group2['content'][group2_expected.index(result)]
            assert result[0] == log_entry['title'],  \
                "Expected title {}. Actual message {}".format(result[0], log_entry['title'])
            assert result[1] == log_entry['message'], \
                "Expected message {}. Actual message {}".format(result[1], log_entry['message'])
            assert result[2] is log_entry['result'], \
                "Expected result {}. Actual result {}".format(result[2], log_entry['result'])


def test_multiple_group_tasks_without_group_title(sdk_client_fs: ADCMClient):
    """Check group task without title.
    """
    bundle_dir = utils.get_data_dir(__file__, 'group_tasks_without_group_title')
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    action = cluster.action_run(name='check_sample')
    action.wait()
    with allure.step('Check log content amount'):
        job = action.job()
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[2].id)
        assert len(log.content) == 2, log.content
    with allure.step('Check title and result in log content'):
        for log_entry in log.content:
            assert log_entry['title'] == 'Check log 1',\
                "Expected title 'Check log 1'. Current title {}".format(log_entry['title'])
            assert log_entry['result'], "Result is False, Expected True"


def test_multiple_tasks_action_with_log_files_check(sdk_client_fs: ADCMClient):
    """Check that log_files parameter don't affect action
    """
    bundle_dir = utils.get_data_dir(__file__, 'log_files_check')
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action_run(name='check_sample')
    task.wait()
    with allure.step('Check if job status is success, action name: check_sample'):
        job = task.job()
        assert job.status == 'success', \
            "Current job status {}. Expected: success".format(job.status)
    with allure.step('Check if result is True.'):
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[2].id)
        content = log.content[0]
        assert content['result'], "Result is False, Expected True"


def test_result_no(sdk_client_fs: ADCMClient):
    """Check config with result no
    """
    bundle_dir = utils.get_data_dir(__file__, "result_no")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action_run(name='adcm_check')
    task.wait()
    with allure.step('Check if job status is success, action name: adcm_check'):
        job = task.job()
        assert job.status == 'success', \
            "Current job status {}. Expected: success".format(job.status)
    with allure.step('Check if result is False.'):
        logs = job.log_list()
        log = job.log(job_id=job.id, log_id=logs[2].id)
        content = log.content[0]
        assert not content['result'], "Result is True, Expected False"
