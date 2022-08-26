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
import itertools
from typing import Collection, List, Optional, Set, Tuple

import allure
import pytest
from adcm_client.objects import ADCM, ADCMClient, Cluster, Component, Host, Provider, Service, Task
from adcm_pytest_plugin.steps.commands import logrotate
from adcm_pytest_plugin.utils import get_data_dir, random_string
from docker.models.containers import Container

from tests.functional.conftest import only_clean_adcm
from tests.library.assertions import does_not_intersect, is_superset_of
from tests.library.db import set_configs_date, set_job_directories_date, set_jobs_date, set_tasks_date

pytestmark = [only_clean_adcm]


SIMPLE_ACTION = 'simple'
MULTIJOB_ACTION = 'multi'


@pytest.fixture()
def objects(sdk_client_fs) -> Tuple[Cluster, Service, Component, Provider, Host]:
    """Create all types of objects"""
    cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    cluster = cluster_bundle.cluster_create('Test Cluster')
    service = cluster.service_add(name='test_service')
    provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'provider'))
    provider = provider_bundle.provider_create(name='Test Provider')
    return cluster, service, service.component(), provider, provider.host_create('some-host-fqdn')


@pytest.fixture()
def simple_tasks(objects) -> List[Task]:
    """Spawn simple tasks (1 job per each) on each object"""
    return _run_action_on_all_objects(SIMPLE_ACTION, objects)


@pytest.fixture()
def multi_tasks(objects) -> List[Task]:
    """Spawn multijobs on each object"""
    return _run_action_on_all_objects(MULTIJOB_ACTION, objects)


@pytest.fixture()
def config_objects(objects) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    """Spawn many configs on each object"""
    configs = [
        [obj.config_set_diff({'param': random_string(12)}) and obj.config(full=True)['id'] for _ in range(10)]
        for obj in objects
    ]
    bonded_configs = tuple(itertools.chain.from_iterable(c[-2:] for c in configs))
    non_bonded_configs = tuple(itertools.chain.from_iterable(c[:-2] for c in configs))
    return bonded_configs, non_bonded_configs


@pytest.fixture()
def config_group_objects(objects) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    """Spawn many object configs on each object except Host"""
    configs = [
        [
            group.config_set_diff({'attr': {'group_keys': {'param': True}}, 'config': {'param': random_string(12)}})
            and group.config(full=True)['id']
            for _ in range(10)
        ]
        for group in [
            obj.group_config_create(f'Group of {obj.__class__.__name__}')
            for obj in filter(lambda o: not isinstance(o, Host), objects)
        ]
    ]
    bonded_configs = tuple(itertools.chain.from_iterable(c[-2:] for c in configs))
    non_bonded_configs = tuple(itertools.chain.from_iterable(c[:-2] for c in configs))
    return bonded_configs, non_bonded_configs


@pytest.fixture()
def separated_configs(config_objects, config_group_objects) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    """Return separately bonded and not bonded configs' and group configs' ids"""
    return (*config_objects[0], *config_group_objects[0]), (*config_objects[1], *config_group_objects[1])


# !===== Tests =====!


def _set_tasks_jobs_date(adcm_fs, adcm_db, date, task_ids, job_ids):
    set_tasks_date(adcm_db, date, task_ids)
    set_jobs_date(adcm_db, date, job_ids)
    set_job_directories_date(adcm_fs.container, date, job_ids)


def test_job_logs_cleanup(sdk_client_fs, adcm_fs, adcm_db, simple_tasks):
    """
    Test that directories with job logs are removed from FS and DB
    when they're too old.
    Plain "logrotate".
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    # since it's a simple jobs, task_id and job_id will be the same
    all_job_ids = [t.id for t in simple_tasks]

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), jobs_in_db=1, jobs_on_fs=1)
    _set_tasks_jobs_date(adcm_fs, adcm_db, ten_days_ago, all_job_ids, all_job_ids)
    logrotate(adcm_fs)

    check_task_logs_are_removed_from_db(sdk_client_fs, all_job_ids)
    check_job_logs_are_removed_from_db(sdk_client_fs, all_job_ids)
    check_job_logs_are_removed_from_fs(adcm_fs.container, all_job_ids)


def test_jobs_cleanup_fs_only(sdk_client_fs, adcm_fs, adcm_db, simple_tasks):
    """
    Test that only directories with job logs are removed only from FS
    when remove from FS setting is != 0 and remove from DB == 0.
    Plain "logrotate".
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    # since it's a simple jobs, task_id and job_id will be the same
    all_job_ids = [t.id for t in simple_tasks]

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), jobs_in_db=0, jobs_on_fs=1)
    _set_tasks_jobs_date(adcm_fs, adcm_db, ten_days_ago, all_job_ids, all_job_ids)
    logrotate(adcm_fs)

    check_job_logs_are_removed_from_fs(adcm_fs.container, all_job_ids)
    check_job_logs_are_presented_in_db(sdk_client_fs, all_job_ids)
    check_task_logs_are_presented_in_db(sdk_client_fs, all_job_ids)


def test_jobs_cleanup_db_only(sdk_client_fs, adcm_fs, adcm_db, simple_tasks):
    """
    Test that only directories with job logs are removed only from DB
    when remove from FS setting is == 0 and remove from DB != 0.
    Plain "logrotate".
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    # since it's a simple jobs, task_id and job_id will be the same
    all_job_ids = [t.id for t in simple_tasks]

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), jobs_in_db=1, jobs_on_fs=0)
    _set_tasks_jobs_date(adcm_fs, adcm_db, ten_days_ago, all_job_ids, all_job_ids)
    logrotate(adcm_fs)

    check_task_logs_are_removed_from_db(sdk_client_fs, all_job_ids)
    check_job_logs_are_removed_from_db(sdk_client_fs, all_job_ids)
    check_job_logs_are_presented_on_fs(adcm_fs.container, all_job_ids)


def test_remove_only_expired_job_logs(sdk_client_fs, adcm_fs, adcm_db, simple_tasks):
    """
    Test that only old enough tasks and jobs are removed.
    Plain "logrotate".
    """
    five_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=5)
    month_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    very_old_job_ids = [t.id for t in simple_tasks[:2]]
    not_so_old_job_ids = [t.id for t in simple_tasks[2:]]

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), jobs_in_db=10, jobs_on_fs=10)
    _set_tasks_jobs_date(adcm_fs, adcm_db, month_ago, very_old_job_ids, very_old_job_ids)
    _set_tasks_jobs_date(adcm_fs, adcm_db, five_days_ago, not_so_old_job_ids, not_so_old_job_ids)
    logrotate(adcm_fs)

    check_task_logs_are_removed_from_db(sdk_client_fs, very_old_job_ids)
    check_task_logs_are_presented_in_db(sdk_client_fs, not_so_old_job_ids)
    check_job_logs_are_removed_from_db(sdk_client_fs, very_old_job_ids)
    check_job_logs_are_presented_in_db(sdk_client_fs, not_so_old_job_ids)
    check_job_logs_are_removed_from_fs(adcm_fs.container, very_old_job_ids)
    check_job_logs_are_presented_on_fs(adcm_fs.container, not_so_old_job_ids)


def test_cleanup_multijobs(sdk_client_fs, adcm_fs, adcm_db, multi_tasks):
    """
    Test that multijobs are cleaned from DB when their parent task is too old
    and tasks are cleaned from FS when jobs themselves are "out of date".
    Plain "logrotate".
    """
    # 5 and 7 picked to distinct threshold clearly
    five_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=5)
    seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    two_day_task, *another_tasks = multi_tasks
    first_task_jobs_ids = first_job_id, *other_job_ids = [j.id for j in two_day_task.job_list()]
    another_tasks_job_ids = list(itertools.chain.from_iterable((t.id for t in t.job_list()) for t in another_tasks))
    old_jobs = (*other_job_ids, *another_tasks_job_ids)

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), jobs_in_db=6, jobs_on_fs=6)
    _set_tasks_jobs_date(adcm_fs, adcm_db, five_days_ago, [two_day_task.id], [first_job_id])
    _set_tasks_jobs_date(adcm_fs, adcm_db, seven_days_ago, [t.id for t in another_tasks], old_jobs)
    logrotate(adcm_fs)

    check_task_logs_are_presented_in_db(sdk_client_fs, [two_day_task.id])
    check_job_logs_are_presented_in_db(sdk_client_fs, first_task_jobs_ids)
    check_job_logs_are_presented_on_fs(adcm_fs.container, [first_job_id])
    check_task_logs_are_removed_from_db(sdk_client_fs, another_tasks)
    check_job_logs_are_removed_from_db(sdk_client_fs, another_tasks_job_ids)
    check_job_logs_are_removed_from_fs(adcm_fs.container, old_jobs)


def test_config_rotation(sdk_client_fs, adcm_fs, adcm_db, separated_configs, objects):
    """
    Test config rotation.
    Plain "logrotate".
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    all_configs, not_bonded_configs = separated_configs

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), config_in_db=1)
    set_configs_date(adcm_db, ten_days_ago)
    logrotate(adcm_fs)

    check_config_logs_are_presented(sdk_client_fs, all_configs)
    check_config_logs_are_removed(sdk_client_fs, not_bonded_configs)
    _check_config_groups_exists(objects)


def test_remove_only_expired_config_logs(sdk_client_fs, adcm_fs, adcm_db, separated_configs, objects):
    """
    Test config rotation removes only old enough configs, but leaves not old enough intact.
    Plain "logrotate".
    """
    five_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=5)
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    bonded_configs, not_bonded_configs = separated_configs
    very_old_configs = [c for i, c in enumerate(not_bonded_configs) if i % 2 == 0]
    not_so_old_configs = [c for i, c in enumerate(not_bonded_configs) if i % 2 != 0]

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), config_in_db=5)
    set_configs_date(adcm_db, ten_days_ago)
    set_configs_date(adcm_db, five_days_ago, not_so_old_configs)
    logrotate(adcm_fs)

    check_config_logs_are_presented(sdk_client_fs, (*bonded_configs, *not_so_old_configs))
    check_config_logs_are_removed(sdk_client_fs, very_old_configs)
    _check_config_groups_exists(objects)


# pylint: disable-next=too-many-arguments
def test_logrotate_command_target_job(sdk_client_fs, adcm_fs, adcm_db, simple_tasks, separated_configs, objects):
    """
    Check that "logrotate --target job" deletes only configs, but not the jobs
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    configs = [*separated_configs[0], *separated_configs[1]]
    job_ids = [t.id for t in simple_tasks]

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), 1, 1, 1)
    set_configs_date(adcm_db, ten_days_ago)
    _set_tasks_jobs_date(adcm_fs, adcm_db, ten_days_ago, job_ids, job_ids)
    logrotate(adcm_fs, target='job')

    check_config_logs_are_presented(sdk_client_fs, configs)
    check_job_logs_are_removed_from_db(sdk_client_fs, job_ids)
    check_job_logs_are_removed_from_fs(adcm_fs.container, job_ids)
    _check_config_groups_exists(objects)


# pylint: disable-next=too-many-arguments
def test_logrotate_command_target_config(sdk_client_fs, adcm_fs, adcm_db, simple_tasks, separated_configs, objects):
    """
    Check that "logrotate --target config" deletes only configs, but not the jobs
    """
    bonded_configs, not_bonded_configs = separated_configs
    job_ids = [t.id for t in simple_tasks]
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), 1, 1, 1)
    set_configs_date(adcm_db, ten_days_ago)
    _set_tasks_jobs_date(adcm_fs, adcm_db, ten_days_ago, job_ids, job_ids)
    logrotate(adcm_fs, target='config')

    check_job_logs_are_presented_in_db(sdk_client_fs, job_ids)
    check_job_logs_are_presented_on_fs(adcm_fs.container, job_ids)
    check_config_logs_are_presented(sdk_client_fs, bonded_configs)
    check_config_logs_are_removed(sdk_client_fs, not_bonded_configs)
    _check_config_groups_exists(objects)


def test_old_adcm_config_removal(sdk_client_fs, adcm_fs, adcm_db):
    """
    Check that ADCM old config logs are removed with plain "logrotate" command
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    adcm = sdk_client_fs.adcm()

    with allure.step('Create 10 ADCM configs'):
        for i in range(1, 11):
            adcm.config_set_diff({'ansible_settings': {'forks': i}})

    set_rotation_info_in_adcm_config(adcm, config_in_db=1)
    adcm_history = [ch['id'] for ch in sorted(adcm.config_history(full=True), key=lambda c: c['date'])]
    set_configs_date(adcm_db, ten_days_ago, adcm_history)
    logrotate(adcm_fs)

    check_config_logs_are_presented(sdk_client_fs, adcm_history[-2:])
    check_config_logs_are_removed(sdk_client_fs, adcm_history[:-2])


def test_only_finished_tasks_removed(sdk_client_fs, adcm_fs, adcm_db, objects):
    """
    Test that running objects aren't removed from DB
    """
    ten_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    cluster, *_ = objects

    with allure.step('Run long action'):
        long_task = cluster.action(name='sleep').run()
    task_ids = [long_task.id]
    job_ids = [long_task.job().id]

    set_rotation_info_in_adcm_config(sdk_client_fs.adcm(), jobs_in_db=1, jobs_on_fs=1)
    _set_tasks_jobs_date(adcm_fs, adcm_db, ten_days_ago, task_ids, job_ids)
    logrotate(adcm_fs)

    if long_task.status != 'running':
        raise ValueError(
            'Long action finished during logrotate OR right after it. Increase sleep time in sleep.yaml file'
        )

    check_task_logs_are_presented_in_db(sdk_client_fs, task_ids)
    check_job_logs_are_presented_in_db(sdk_client_fs, job_ids)


# !===== Steps =====!

# set dates and configs


def set_rotation_info_in_adcm_config(
    adcm: ADCM, jobs_in_db: Optional[int] = None, jobs_on_fs: Optional[int] = None, config_in_db: Optional[int] = None
) -> dict:
    """Update ADCM config with new jobs/config log rotation info"""
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
        config['config_rotation'] = {'config_rotation_in_db': config_in_db}
    with allure.step("Change ADCM config's rotation settings"):
        return adcm.config_set_diff(config)


# !===== Checks =====!


# absence checks


def check_task_logs_are_removed_from_db(client: ADCMClient, task_ids: Collection[int]):
    """Check task logs are removed from the database"""
    with allure.step(f'Check that task logs are removed from DB: {", ".join(map(str, task_ids))}'):
        presented_task_ids = {job.task().id for job in client.job_list()}
        does_not_intersect(
            presented_task_ids, task_ids, 'Some of the task logs that should be removed were found in db'
        )


def check_job_logs_are_removed_from_db(client: ADCMClient, job_ids: Collection[int]):
    """Check job logs are removed from the database"""
    with allure.step(f'Check that job logs are removed from DB: {", ".join(map(str, job_ids))}'):
        presented_job_ids = {job.id for job in client.job_list()}
        does_not_intersect(presented_job_ids, job_ids, 'Some of the job logs that should be removed were found in db')


def check_job_logs_are_removed_from_fs(container: Container, job_ids: Collection[int]):
    """Check job logs are removed from the filesystem"""
    with allure.step(f'Check that job logs are removed from FS: {", ".join(map(str, job_ids))}'):
        presented_tasks = _get_ids_of_job_logs_on_fs(container)
        does_not_intersect(
            presented_tasks, set(job_ids), 'Some of the job logs that should be removed were found on filesystem'
        )


def check_config_logs_are_removed(client: ADCMClient, config_ids: Collection[int]):
    """Check config logs are removed from the database"""
    with allure.step(f'Check that config logs are removed from DB: {", ".join(map(str, config_ids))}'):
        presented_configs = _retrieve_config_ids(client)
        does_not_intersect(
            presented_configs, set(config_ids), 'Some of the config logs that should be removed were found in db'
        )


# existence checks


def check_job_logs_are_presented_in_db(client: ADCMClient, job_ids: Collection[int]):
    """Check job logs are presented in the database"""
    with allure.step(f'Check that job logs are presented in DB: {", ".join(map(str, job_ids))}'):
        presented_job_ids = {job.id for job in client.job_list()}
        is_superset_of(presented_job_ids, job_ids, 'Not all job logs are presented in database')


def check_task_logs_are_presented_in_db(client: ADCMClient, task_ids: Collection[int]):
    """Check task logs are presented in the database"""
    with allure.step(f'Check that task logs are presented in DB: {", ".join(map(str, task_ids))}'):
        presented_task_ids = {job.task().id for job in client.job_list()}
        is_superset_of(presented_task_ids, task_ids, 'Not all task logs are presented in database')


def check_job_logs_are_presented_on_fs(container: Container, job_ids: Collection[int]):
    """Check that job logs are presented on the filesystem"""
    with allure.step(f'Check that job logs are presented on FS: {", ".join(map(str, job_ids))}'):
        presented_tasks = _get_ids_of_job_logs_on_fs(container)
        is_superset_of(presented_tasks, job_ids, 'Not all job logs are presented on filesystem')


def check_config_logs_are_presented(client: ADCMClient, config_ids: Collection[int]):
    """Check that config logs are presented in the database"""
    with allure.step(f'Check that config logs are presented in DB: {", ".join(map(str, config_ids))}'):
        presented_configs = _retrieve_config_ids(client)
        is_superset_of(presented_configs, config_ids, 'Not all config logs are presented in database')


# other checks


def _check_config_groups_exists(objects):
    """Check that there's at least one config group presented on each object except Host"""
    for obj in filter(lambda o: not isinstance(o, Host), objects):
        assert len(obj.group_config()) > 0, f'At least one group should be presented on object {obj.__class__.__name__}'


# !===== Utilities =====!


def _get_ids_of_job_logs_on_fs(container: Container) -> Set[int]:
    exit_code, output = container.exec_run(['ls', '/adcm/data/run/'])
    if exit_code != 0:
        raise ValueError(f'Command execution failed: {output}')
    return set(map(int, filter(lambda x: x.isnumeric(), output.decode('utf-8').strip().split('\n'))))


def _retrieve_config_ids(client: ADCMClient) -> Set[int]:
    all_objects = list(
        itertools.chain.from_iterable(
            getattr(client, f'{type_name}_list')()
            for type_name in ('cluster', 'service', 'component', 'provider', 'host')
        )
    )
    all_objects += list(
        itertools.chain.from_iterable(
            obj.group_config() for obj in filter(lambda o: not isinstance(o, Host), all_objects)
        )
    )
    all_objects.append(client.adcm())
    return {c['id'] for c in itertools.chain.from_iterable(obj.config_history(full=True) for obj in all_objects)}


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
