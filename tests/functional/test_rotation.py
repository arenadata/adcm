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

"""Test rotation of job logs and unattached configs"""

# pylint: disable=redefined-outer-name

import datetime

from typing import Collection, Tuple, List, Optional, Set

import pytest
from adcm_client.objects import ADCM, ADCMClient, Cluster, Service, Component, Provider, Host, Task
from adcm_pytest_plugin.utils import get_data_dir, wait_until_step_succeeds
from docker.models.containers import Container

from tests.functional.conftest import only_clean_adcm
from tests.library.assertions import does_not_intersect, is_superset_of
from tests.library.db import QueryExecutioner, Query

pytestmark = [only_clean_adcm]

CONFIG_LOG_TABLE = 'cm_configlog'
JOB_LOG_TABLE = 'cm_joblog'
TASK_LOG_TABLE = 'cm_tasklog'
LOG_STORAGE_TABLE = 'cm_logstorage'

SIMPLE_ACTION = 'simple'
MULTIJOB_ACTION = 'multi'


@pytest.fixture()
def objects(sdk_client_fs) -> Tuple[Cluster, Service, Component, Provider, Host]:
    cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    cluster = cluster_bundle.cluster_create('Test Cluster')
    service = cluster.service_add(name='test_service')
    provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'provider'))
    provider = provider_bundle.provider_create(name='Test Provider')
    return cluster, service, service.component(), provider, provider.host_create('some-host-fqdn')


def _all_tasks_finished(tasks):
    for task in tasks:
        task.wait()


def _run_action_on_all_objects(action_name, objects) -> List[Task]:
    cluster, service, component, provider, host = objects
    tasks = [cluster.action(name=action_name).run(), provider.action(name=action_name).run()]
    _all_tasks_finished(tasks)
    tasks.append(service.action(name=action_name).run())
    tasks.append(host.action(name=action_name).run())
    _all_tasks_finished(tasks)
    tasks.append(component.action(name=action_name).run())
    _all_tasks_finished(tasks)
    return tasks


@pytest.fixture()
def simple_tasks(objects) -> List[Task]:
    return _run_action_on_all_objects(SIMPLE_ACTION, objects)


@pytest.fixture()
def multi_tasks(objects) -> List[Task]:
    return _run_action_on_all_objects(MULTIJOB_ACTION, objects)


# !===== Tests =====!


def _set_tasks_jobs_date(adcm_fs, adcm_db, date, task_ids, job_ids):
    set_tasks_date(adcm_db, date, task_ids)
    set_jobs_date(adcm_db, date, job_ids)
    set_job_directories_date(adcm_fs.container, date, job_ids)


def test_job_logs_cleanup(sdk_client_fs, adcm_fs, adcm_db, simple_tasks):
    """
    Test that directories with job logs are removed from FS and DB
    when they're too old
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    # since it's a simple jobs, task_id and job_id will be the same
    all_job_ids = [t.id for t in simple_tasks]

    _set_tasks_jobs_date(adcm_fs, adcm_db, ten_days_ago, all_job_ids, all_job_ids)

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), jobs_in_db=1, jobs_on_fs=1)
    wait_until_step_succeeds(check_task_logs_are_removed_from_db, 120, client=sdk_client_fs, task_ids=all_job_ids)
    wait_until_step_succeeds(check_job_logs_are_removed_from_db, 120, client=sdk_client_fs, job_ids=all_job_ids)
    wait_until_step_succeeds(check_job_logs_are_removed_from_fs, 120, container=adcm_fs.container, job_ids=all_job_ids)


def test_jobs_cleanup_fs_only(sdk_client_fs, adcm_fs, adcm_db, simple_tasks):
    """
    Test that only directories with job logs are removed only from FS
    when remove from FS setting is != 0 and remove from DB == 0
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    # since it's a simple jobs, task_id and job_id will be the same
    all_job_ids = [t.id for t in simple_tasks]

    _set_tasks_jobs_date(adcm_fs, adcm_db, ten_days_ago, all_job_ids, all_job_ids)

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), jobs_in_db=0, jobs_on_fs=1)
    wait_until_step_succeeds(check_job_logs_are_removed_from_fs, 120, container=adcm_fs.container, job_ids=all_job_ids)
    check_job_logs_are_presented_in_db(sdk_client_fs, all_job_ids)
    check_task_logs_are_presented_in_db(sdk_client_fs, all_job_ids)


def test_jobs_cleanup_db_only(sdk_client_fs, adcm_fs, adcm_db, simple_tasks):
    """
    Test that only directories with job logs are removed only from DB
    when remove from FS setting is == 0 and remove from DB != 0
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    # since it's a simple jobs, task_id and job_id will be the same
    all_job_ids = [t.id for t in simple_tasks]

    _set_tasks_jobs_date(adcm_fs, adcm_db, ten_days_ago, all_job_ids, all_job_ids)

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), jobs_in_db=1, jobs_on_fs=0)
    wait_until_step_succeeds(check_task_logs_are_removed_from_db, 120, client=sdk_client_fs, task_ids=all_job_ids)
    wait_until_step_succeeds(check_job_logs_are_removed_from_db, 120, client=sdk_client_fs, job_ids=all_job_ids)
    check_job_logs_are_presented_on_fs(adcm_fs.container, all_job_ids)


def test_remove_only_expired_job_logs():
    ...


def test_cleanup_multijobs():
    ...


def test_config_rotation(sdk_client_fs, adcm_db):
    make_config_10_days_old = Query('cm_configlog').update(
        [('date', datetime.datetime.utcnow() - datetime.timedelta(days=10))]
    )
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    cluster = bundle.cluster_create('HeheHoho')
    configs = [cluster.config_set_diff({'param': str(i)}) for i in range(10)]
    adcm_db.exec(make_config_10_days_old)
    cluster


# remove checks


def check_task_logs_are_removed_from_db(client: ADCMClient, task_ids: Collection[int]):
    presented_task_ids = {job.task().id for job in client.job_list()}
    does_not_intersect(presented_task_ids, task_ids, 'Some of the task logs that should be removed were found in db')


def check_job_logs_are_removed_from_db(client: ADCMClient, job_ids: Collection[int]):
    presented_job_ids = {job.id for job in client.job_list()}
    does_not_intersect(presented_job_ids, job_ids, 'Some of the job logs that should be removed were found in db')


def check_job_logs_are_removed_from_fs(container: Container, job_ids: Collection[int]):
    presented_tasks = _get_ids_of_job_logs_on_fs(container)
    does_not_intersect(
        presented_tasks, set(job_ids), 'Some of the job logs that should be removed were found on filesystem'
    )


# present checks


def check_job_logs_are_presented_in_db(client: ADCMClient, job_ids: Collection[int]):
    presented_job_ids = {job.id for job in client.job_list()}
    is_superset_of(presented_job_ids, job_ids, 'Not all job logs are presented in database')


def check_task_logs_are_presented_in_db(client: ADCMClient, task_ids: Collection[int]):
    presented_task_ids = {job.task().id for job in client.job_list()}
    is_superset_of(presented_task_ids, task_ids, 'Not all task logs are presented in database')


def check_job_logs_are_presented_on_fs(container: Container, job_ids: Collection[int]):
    presented_tasks = _get_ids_of_job_logs_on_fs(container)
    is_superset_of(presented_tasks, job_ids, 'Not all job logs are presented on filesystem')


# set dates and configs


def set_rotation_info_in_adcm_config(
    adcm: ADCM, jobs_in_db: Optional[int] = None, jobs_on_fs: Optional[int] = None, config_in_db: Optional[int] = None
) -> dict:
    # `is not None` because 0 is a legit value
    if not (jobs_in_db is not None or jobs_on_fs is not None or config_in_db is not None):
        raise ValueError('At least one of rotation fields should be provided to set rotation info in ADCM config')
    config = {}
    if jobs_on_fs is not None:
        if 'job_log' not in config:
            config['job_log'] = {}
        config['job_log']['log_rotation_on_fs'] = jobs_on_fs
    if jobs_in_db is not None:
        if 'job_log' not in config:
            config['job_log'] = {}
        config['job_log']['log_rotation_in_db'] = jobs_in_db
    if config_in_db is not None:
        config['config_rotation']['config_rotation_in_db'] = config_in_db
    return adcm.config_set_diff(config)


def set_config_date(adcm_db: QueryExecutioner, date: datetime.datetime, ids: Collection[int] = ()):
    query = Query(CONFIG_LOG_TABLE).update([('date', date)])
    if ids:
        query.where(id=ids)
    adcm_db.exec(query)


def set_jobs_date(adcm_db: QueryExecutioner, date: datetime.datetime, ids: Collection[int] = ()):
    query = Query(JOB_LOG_TABLE).update([('start_date', date), ('finish_date', date)])
    if ids:
        query.where(id=ids)
    adcm_db.exec(query)


def set_tasks_date(adcm_db: QueryExecutioner, date: datetime.datetime, ids: Collection[int] = ()):
    query = Query(TASK_LOG_TABLE).update([('start_date', date), ('finish_date', date)])
    if ids:
        query.where(id=ids)
    adcm_db.exec(query)


def set_job_directories_date(container: Container, date: datetime.datetime, ids: Collection[int]):
    strdate = date.strftime("%Y%m%d%H%M")
    for id_ in ids:
        exit_code, output = container.exec_run(['touch', '-t', strdate, f'/adcm/data/run/{id_}/'])
        if exit_code != 0:
            raise ValueError(
                f"Failed to set modification date ('{strdate}') to job dir with id {id_}.\n'"
                f"f'Output:\n{output.decode('utf-8')}"
            )


def _get_ids_of_job_logs_on_fs(container: Container) -> Set[int]:
    exit_code, output = container.exec_run(['ls', '/adcm/data/run/'])
    if exit_code != 0:
        raise ValueError(f'Command execution failed: {output}')
    return set(map(int, filter(lambda x: x.isnumeric(), output.decode('utf-8').strip().split('\n'))))
