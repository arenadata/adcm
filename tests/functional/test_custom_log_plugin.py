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

"""Tests for custom log plugin"""

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils

FORMAT_STORAGE = ["json_path", "json_content", 'txt_path', "txt_content"]
FIELD = ['name', 'format', 'storage_type']


@pytest.mark.parametrize("bundle", FIELD)
def test_required_fields(sdk_client_fs: ADCMClient, bundle):
    """Task should be failed if required field not presented"""
    stack_dir = utils.get_data_dir(__file__, "required_fields", f"no_{bundle}")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name='custom_log').run()
    task.wait()
    with allure.step('Check job state'):
        assert task.status == 'failed', f"Current job status {task.status}. Expected: failed"
    with allure.step('Check if logs are equal 2'):
        job = task.job()
        logs = job.log_list()
        assert len(logs) == 2, f"Logs count not equal 2, current log count {len(logs)}"


@pytest.mark.parametrize("bundle", FORMAT_STORAGE)
def test_different_storage_types_with_format(sdk_client_fs: ADCMClient, bundle):
    """Check different combinations of storage and format"""
    log_format = bundle.split("_")[0]
    stack_dir = utils.get_data_dir(__file__, bundle)
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name='custom_log').run()
    task.wait()
    with allure.step('Check if logs are equal 3, job state and logs'):
        job = task.job()
        logs = job.log_list()
        assert len(logs) == 3, f"Logs count {len(logs)}. Expected 3"
        assert job.status == 'success', f"Current job status {job.status}. Expected: success"
        log = logs[2]
        err_msg = f"Expected log format {log_format}. Actual log format {log.format}"
        assert log.format == log_format, err_msg
        assert log.type == 'custom'


def test_path_and_content(sdk_client_fs: ADCMClient):
    """If path and content presented we need to get path, not content"""
    stack_dir = utils.get_data_dir(__file__, "path_and_content")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name='custom_log').run()
    task.wait()
    with allure.step('Check logs content and format'):
        job = task.job()
        logs = job.log_list()
        log = logs[2]
        assert log.content == '{\n    "key": "value"\n}'
        assert log.format == 'json'


@pytest.mark.parametrize("bundle", ['equal_pathes', 'equal_names', 'equal_pathes_and_names'])
def test_multiple_tasks(sdk_client_fs: ADCMClient, bundle):
    """Check situation when we have multiple tasks"""
    stack_dir = utils.get_data_dir(__file__, bundle)
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name='custom_log').run()
    task.wait()
    with allure.step('Check 4 logs entries'):
        logs = task.job().log_list()
        assert len(logs) == 4, "Expected 4 logs entries, because 2 tasks in playbook"


def test_check_text_file_content(sdk_client_fs: ADCMClient):
    """Check that text content from file correct"""
    stack_dir = utils.get_data_dir(__file__, "txt_path")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name='custom_log').run()
    task.wait()
    with allure.step('Check logs content and format'):
        job = task.job()
        log = job.log_list()[2]
        assert log.content == 'Hello world!\n'
        assert log.format == 'txt'


def test_check_text_content(sdk_client_fs: ADCMClient):
    """Check that text content correct"""
    stack_dir = utils.get_data_dir(__file__, "txt_content")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name='custom_log').run()
    task.wait()
    with allure.step('Check logs content'):
        job = task.job()
        log = job.log_list()[2]
        assert log.content == 'shalala'


def test_check_json_content(sdk_client_fs: ADCMClient):
    """Check that json content correct"""
    stack_dir = utils.get_data_dir(__file__, "json_content")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name='custom_log').run()
    task.wait()
    with allure.step('Check logs content'):
        job = task.job()
        log = job.log_list()[2]
        assert log.content == '{\n    "hello": "world"\n}'


def test_incorrect_syntax_for_fields(sdk_client_fs: ADCMClient):
    """Check if we have not json in content"""
    stack_dir = utils.get_data_dir(__file__, "syntax_for_fields")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name='custom_log').run()
    task.wait()
    with allure.step('Check logs content'):
        job = task.job()
        log = job.log_list()[2]
        assert log.content == '{1: "world"}'
