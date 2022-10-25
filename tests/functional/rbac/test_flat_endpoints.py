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
Test endpoints that are placed in the root to access "nested" objects like configs and jobs
"""
import itertools

import allure
import pytest
import requests
from adcm_client.objects import Cluster, Host, ADCMClient, ADCM
from adcm_pytest_plugin.utils import random_string

from tests.functional.rbac.conftest import RbacRoles
from tests.library.assertions import sets_are_equal
from tests.library.utils import lower_class_name

ACTION_NAME = 'no_config'

CONFIG_EP = 'config'
CONFIG_LOG_EP = 'config-log'
GROUP_CONFIG_EP = 'group-config'


@pytest.fixture()
def _prepare_configs(prepare_objects, second_objects) -> None:
    """Change configs, crete group configs and change them"""
    changed_config = {'boolean': False}
    for first_object, second_object in zip(prepare_objects, second_objects):
        first_object.config_set_diff(changed_config)
        second_object.config_set_diff(changed_config)
        if not isinstance(first_object, Host):
            _prepare_group_config(first_object)
            _prepare_group_config(second_object)


@pytest.mark.usefixtures('_prepare_configs')
def test_flat_endpoints(user, clients, prepare_objects, second_objects):
    """
    Test "flat" endpoints:
      job/
      task/
      group-config/
      config-log/
      config/
    """
    cluster, service, component, provider, host = prepare_objects
    all_objects = [*second_objects, cluster, service, provider, host, *service.component_list(), clients.admin.adcm()]

    clients.admin.policy_create(
        name=f'Service administrator of {service.name}',
        role=clients.admin.role(name=RbacRoles.ServiceAdministrator.value),
        objects=[service],
        user=[user],
        group=[],
    )

    _run_actions(prepare_objects, second_objects)

    with allure.step('Check flat endpoints from the Admin perspective'):
        check_jobs_and_tasks(clients.admin, prepare_objects + second_objects)
        check_configs(clients.admin, all_objects)

    with allure.step('Check flat endpoints from the User perspective'):
        # action was executed only on one component
        check_jobs_and_tasks(clients.user, (service, component))
        check_configs(clients.user, (service, *service.component_list()))


def check_jobs_and_tasks(client: ADCMClient, objects):
    """
    Check that only correct jobs and tasks are listed in flat endpoints
    based on "owner" objects
    """
    job_flat_endpoint = "job"
    task_flat_endpoint = "task"

    with allure.step(f'Check jobs at "{job_flat_endpoint}/" endpoint based on task_id'):
        expected_jobs = set()
        for task in itertools.chain.from_iterable([obj.action(name=ACTION_NAME).task_list() for obj in objects]):
            expected_jobs |= {job.id for job in task.job_list()}
        actual_jobs: set = {job['id'] for job in _query_flat_endpoint(client, job_flat_endpoint)}
        sets_are_equal(
            actual_jobs,
            expected_jobs,
            f'Jobs at flat endpoint "{job_flat_endpoint}/" is not the ones that were expected',
        )

    with allure.step(f'Check tasks at "{task_flat_endpoint}/" endpoint based on object_id and action_id'):
        expected_tasks: set = {(obj.id, obj.action(name=ACTION_NAME).id) for obj in objects}
        actual_tasks: set = {
            (task['object_id'], task['action_id']) for task in _query_flat_endpoint(client, task_flat_endpoint)
        }
        sets_are_equal(
            actual_tasks,
            expected_tasks,
            f'Tasks at flat endpoint "{task_flat_endpoint}/" is not the ones that were expected',
        )


def check_configs(client: ADCMClient, objects):
    """Check configs, config groups and config logs"""
    objects_with_group_config = _check_group_config_endpoint(client, objects)
    expected_config_logs = _check_config_logs_endpoint(client, objects, objects_with_group_config)
    _check_configs_endpoint(client, expected_config_logs)


@allure.step(f'Check tasks at "{GROUP_CONFIG_EP}/" endpoint based on object type, object_id and config_id')
def _check_group_config_endpoint(client, objects):
    objects_with_group_config = tuple(
        filter(lambda x: not isinstance(x, Host) and not isinstance(x, ADCM) and x.group_config(), objects)
    )
    expected_group_configs = {
        (lower_class_name(obj), obj.id, obj.group_config()[0].config_id) for obj in objects_with_group_config
    }
    actual_group_configs = {
        (group_config['object_type'], group_config['object_id'], group_config['config_id'])
        for group_config in _query_flat_endpoint(client, GROUP_CONFIG_EP)
    }
    sets_are_equal(
        actual_group_configs,
        expected_group_configs,
        f'Group configs at flat endpoint "{GROUP_CONFIG_EP}"/ are not the same as expected',
    )
    return objects_with_group_config


@allure.step(f'Check config logs at "{CONFIG_LOG_EP}/" endpoint based on config_id')
def _check_config_logs_endpoint(client, objects, objects_with_group_config):
    expected_config_logs = {
        config['id'] for config in itertools.chain.from_iterable([obj.config_history(full=True) for obj in objects])
    } | {
        config_log['id']
        for config_log in itertools.chain.from_iterable(
            _get_history_of_group_config(client, obj.group_config()[0]) for obj in objects_with_group_config
        )
    }
    actual_config_logs = {config['id'] for config in _query_flat_endpoint(client, CONFIG_LOG_EP)}
    sets_are_equal(
        actual_config_logs,
        expected_config_logs,
        f'Config logs at flat endpoint "{CONFIG_LOG_EP}/" are not the same as expected',
    )
    return expected_config_logs


@allure.step(f'Check configs at "{CONFIG_EP}/" endpoint based on config_id (obj_ref)')
def _check_configs_endpoint(client, expected_config_logs):
    # at this point we sure that we see only the things we are allowed to see
    expected_configs = {
        config['obj_ref']
        for config in _query_flat_endpoint(client, CONFIG_LOG_EP)
        if config['id'] in expected_config_logs
    }
    actual_configs = {config['id'] for config in _query_flat_endpoint(client, CONFIG_EP)}
    sets_are_equal(
        actual_configs, expected_configs, f'Configs at flat endpoint "{CONFIG_EP}/" are not the same as expected'
    )


@allure.step('Run action on all objects')
def _run_actions(first_objects, second_objects):
    for first, second in zip(first_objects, second_objects):
        task = first.action(name=ACTION_NAME).run()
        second.action(name=ACTION_NAME).run().wait()
        task.wait()


def _query_flat_endpoint(client: ADCMClient, endpoint: str):
    response = requests.get(
        f'{client.url}/api/v1/{endpoint}/', headers={'Authorization': f'Token {client.api_token()}'}
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return data
    return data['results']


def _prepare_group_config(adcm_object: Cluster):
    group = adcm_object.group_config_create(f'{adcm_object.name} group {random_string(4)}')
    group.config_set_diff(
        {'config': {'boolean': True}, 'attr': {'group_keys': {'boolean': True}, 'custom_group_keys': {'boolean': True}}}
    )


def _get_history_of_group_config(client, group_config):
    config_id = group_config.config(full=True)['url'].split('/')[-4]
    result = _query_flat_endpoint(client, f'group-config/{group_config.id}/config/{config_id}/config-log/')
    return result
