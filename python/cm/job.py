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

# pylint: disable=too-many-arguments

import json
import os
import shutil
import signal
import subprocess
import time
from collections import defaultdict
from configparser import ConfigParser
from datetime import timedelta, datetime

from background_task import background
from django.db import transaction
from django.utils import timezone

from cm import config
from cm import api, issue, inventory, adcm_config, variant
from cm.adcm_config import obj_ref, process_file_type
from cm.errors import raise_AdcmEx as err
from cm.inventory import get_obj_config, process_config_and_attr
from cm.lock import lock_objects, unlock_objects
from cm.logger import log
from cm.models import (
    Cluster,
    Action,
    SubAction,
    TaskLog,
    JobLog,
    CheckLog,
    Host,
    ADCM,
    ClusterObject,
    HostComponent,
    ServiceComponent,
    HostProvider,
    DummyData,
    LogStorage,
    ConfigLog,
    GroupCheckLog,
    get_object_cluster,
    get_model_by_type,
)
from cm.status_api import Event, post_event


def start_task(action, obj, conf, attr, hc, hosts, verbose):
    if action.type not in ['task', 'job']:
        msg = f'unknown type "{action.type}" for action: {action}, {action.context}: {obj.name}'
        err('WRONG_ACTION_TYPE', msg)

    event = Event()
    task = prepare_task(action, obj, conf, attr, hc, hosts, event, verbose)
    event.send_state()
    run_task(task, event)
    event.send_state()
    log_rotation()

    return task


def check_task(action, obj, cluster, conf):
    check_action_state(action, obj, cluster)
    iss = issue.aggregate_issues(obj)
    if not issue.issue_to_bool(iss):
        err('TASK_ERROR', 'action has issues', iss)


def check_action_hosts(action, obj, cluster, hosts):
    provider = None
    if obj.prototype.type == 'provider':
        provider = obj
    if not hosts:
        return
    if not action.partial_execution:
        err('TASK_ERROR', 'Only action with partial_execution permission can receive host list')
    if not isinstance(hosts, list):
        err('TASK_ERROR', 'Hosts should be array')
    for host_id in hosts:
        if not isinstance(host_id, int):
            err('TASK_ERROR', f'host id should be integer ({host_id})')
        host = Host.obj.get(id=host_id)
        if cluster and host.cluster != cluster:
            err('TASK_ERROR', f'host #{host_id} does not belong to cluster #{cluster.id}')
        if provider and host.provider != provider:
            err('TASK_ERROR', f'host #{host_id} does not belong to host provider #{provider.id}')


def prepare_task(
    action, obj, conf, attr, hc, hosts, event, verbose
):  # pylint: disable=too-many-locals
    cluster = get_object_cluster(obj)
    check_task(action, obj, cluster, conf)
    _, spec = check_action_config(action, obj, conf, attr)
    host_map, delta = check_hostcomponentmap(cluster, action, hc)
    check_action_hosts(action, obj, cluster, hosts)
    old_hc = api.get_hc(cluster)

    if not attr:
        attr = {}

    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())
        lock_objects(obj, event)

        if host_map:
            api.save_hc(cluster, host_map)

        if action.type == 'task':
            task = create_task(action, obj, conf, attr, old_hc, delta, hosts, event, verbose)
        else:
            task = create_one_job_task(action, obj, conf, attr, old_hc, hosts, event, verbose)
            create_job(action, None, event, task)

        if conf:
            new_conf = process_config_and_attr(task, conf, attr, spec)
            process_file_type(task, spec, conf)
            task.config = new_conf
            task.save()

    return task


def restart_task(task):
    event = Event()
    if task.status in (config.Job.CREATED, config.Job.RUNNING):
        err('TASK_ERROR', f'task #{task.id} is running')
    elif task.status == config.Job.SUCCESS:
        run_task(task, event)
        event.send_state()
    elif task.status in (config.Job.FAILED, config.Job.ABORTED):
        run_task(task, event, 'restart')
        event.send_state()
    else:
        err('TASK_ERROR', f'task #{task.id} has unexpected status: {task.status}')


def cancel_task(task):
    errors = {
        config.Job.FAILED: ('TASK_IS_FAILED', f'task #{task.id} is failed'),
        config.Job.ABORTED: ('TASK_IS_ABORTED', f'task #{task.id} is aborted'),
        config.Job.SUCCESS: ('TASK_IS_SUCCESS', f'task #{task.id} is success'),
    }
    action = Action.objects.get(id=task.action_id)
    if not action.allow_to_terminate:
        err(
            'NOT_ALLOWED_TERMINATION',
            f'not allowed termination task #{task.id} for action #{action.id}',
        )
    if task.status in [config.Job.FAILED, config.Job.ABORTED, config.Job.SUCCESS]:
        err(*errors.get(task.status))
    i = 0
    while not JobLog.objects.filter(task=task, status=config.Job.RUNNING) and i < 10:
        time.sleep(0.5)
        i += 1
    if i == 10:
        err('NO_JOBS_RUNNING', 'no jobs running')
    os.kill(task.pid, signal.SIGTERM)


def get_host_object(action, cluster):
    if action.prototype.type == 'service':
        obj = ClusterObject.obj.get(cluster=cluster, prototype=action.prototype)
    elif action.prototype.type == 'component':
        obj = ServiceComponent.obj.get(cluster=cluster, prototype=action.prototype)
    elif action.prototype.type == 'cluster':
        obj = cluster
    return obj


def check_action_state(action, task_object, cluster):
    if action.host_action:
        obj = get_host_object(action, cluster)
    else:
        obj = task_object

    if obj.state == config.Job.LOCKED:
        err('TASK_ERROR', 'object is locked')
    available = action.state_available
    if available == 'any':
        return
    if obj.state in available:
        return
    log.debug('QQ %s', obj)
    err('TASK_ERROR', 'action is disabled')


def check_action_config(action, obj, conf, attr):
    proto = action.prototype
    spec, flat_spec, _, _ = adcm_config.get_prototype_config(proto, action)
    if not spec:
        return None, None
    if not conf:
        err('TASK_ERROR', 'action config is required')
    obj_conf = None
    if obj.config:
        cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
        obj_conf = cl.config
    adcm_config.check_attr(proto, attr, flat_spec)
    variant.process_variant(obj, spec, obj_conf)
    new_conf = adcm_config.check_config_spec(proto, action, spec, flat_spec, conf, None, attr)
    return new_conf, spec


def add_to_dict(my_dict, key, subkey, value):
    if key not in my_dict:
        my_dict[key] = {}
    my_dict[key][subkey] = value


def check_action_hc(action_hc, service, component, action):
    for item in action_hc:
        if item['service'] == service and item['component'] == component:
            if item['action'] == action:
                return True
    return False


def cook_comp_key(name, subname):
    return f'{name}.{subname}'


def cook_delta(cluster, new_hc, action_hc, old=None):  # pylint: disable=too-many-branches
    def add_delta(delta, action, key, fqdn, host):
        service, comp = key.split('.')
        if not check_action_hc(action_hc, service, comp, action):
            msg = (
                f'no permission to "{action}" component "{comp}" of '
                f'service "{service}" to/from hostcomponentmap'
            )
            err('WRONG_ACTION_HC', msg)
        add_to_dict(delta[action], key, fqdn, host)

    new = {}
    for service, host, comp in new_hc:
        key = cook_comp_key(service.prototype.name, comp.prototype.name)
        add_to_dict(new, key, host.fqdn, host)

    if not old:
        old = {}
        for hc in HostComponent.objects.filter(cluster=cluster):
            key = cook_comp_key(hc.service.prototype.name, hc.component.prototype.name)
            add_to_dict(old, key, hc.host.fqdn, hc.host)

    delta = {'add': {}, 'remove': {}}
    for key in new:
        if key in old:
            for host in new[key]:
                if host not in old[key]:
                    add_delta(delta, 'add', key, host, new[key][host])
            for host in old[key]:
                if host not in new[key]:
                    add_delta(delta, 'remove', key, host, old[key][host])
        else:
            for host in new[key]:
                add_delta(delta, 'add', key, host, new[key][host])

    for key in old:
        if key not in new:
            for host in old[key]:
                add_delta(delta, 'remove', key, host, old[key][host])

    log.debug('OLD: %s', old)
    log.debug('NEW: %s', new)
    log.debug('DELTA: %s', delta)
    return delta


def check_hostcomponentmap(cluster, action, hc):
    if not action.hostcomponentmap:
        return None, {'added': {}, 'removed': {}}

    if not hc:
        err('TASK_ERROR', 'hc is required')

    if not cluster:
        err('TASK_ERROR', 'Only cluster objects can have action with hostcomponentmap')

    hostmap = api.check_hc(cluster, hc)
    return hostmap, cook_delta(cluster, hostmap, action.hostcomponentmap)


def check_service_task(cluster_id, action):
    cluster = Cluster.obj.get(id=cluster_id)
    try:
        service = ClusterObject.objects.get(cluster=cluster, prototype=action.prototype)
        return service
    except ClusterObject.DoesNotExist:
        msg = (
            f'service #{action.prototype.id} for action '
            f'"{action.name}" is not installed in cluster #{cluster.id}'
        )
        return err('CLUSTER_SERVICE_NOT_FOUND', msg)


def check_component_task(cluster_id, action):
    cluster = Cluster.obj.get(id=cluster_id)
    try:
        component = ServiceComponent.objects.get(cluster=cluster, prototype=action.prototype)
        return component
    except ServiceComponent.DoesNotExist:
        msg = (
            f'component #{action.prototype.id} for action '
            f'"{action.name}" is not installed in cluster #{cluster.id}'
        )
        return err('COMPONENT_NOT_FOUND', msg)


def check_cluster(cluster_id):
    return Cluster.obj.get(id=cluster_id)


def check_provider(provider_id):
    return HostProvider.obj.get(id=provider_id)


def check_adcm(adcm_id):
    return ADCM.obj.get(id=adcm_id)


def get_bundle_root(action):
    if action.prototype.type == 'adcm':
        return os.path.join(config.BASE_DIR, 'conf')
    return config.BUNDLE_DIR


def cook_script(action, sub_action):
    prefix = action.prototype.bundle.hash
    script = action.script
    if sub_action:
        script = sub_action.script
    if script[0:2] == './':
        script = os.path.join(action.prototype.path, script[2:])
    return os.path.join(get_bundle_root(action), prefix, script)


def get_adcm_config():
    adcm = ADCM.obj.get()
    return get_obj_config(adcm)


def get_new_hc(cluster):
    new_hc = []
    for hc in HostComponent.objects.filter(cluster=cluster):
        new_hc.append((hc.service, hc.host, hc.component))
    return new_hc


def get_old_hc(saved_hc):
    if not saved_hc:
        return {}
    old_hc = {}
    for hc in saved_hc:
        service = ClusterObject.objects.get(id=hc['service_id'])
        comp = ServiceComponent.objects.get(id=hc['component_id'])
        host = Host.objects.get(id=hc['host_id'])
        key = cook_comp_key(service.prototype.name, comp.prototype.name)
        add_to_dict(old_hc, key, host.fqdn, host)
    return old_hc


def re_prepare_job(task, job):
    conf = None
    hosts = None
    delta = {}
    if task.config:
        conf = task.config
    if task.hosts:
        hosts = task.hosts
    action = task.action
    obj = task.task_object
    cluster = get_object_cluster(obj)
    sub_action = None
    if job.sub_action_id:
        sub_action = job.sub_action
    if action.hostcomponentmap:
        new_hc = get_new_hc(cluster)
        old_hc = get_old_hc(task.hostcomponentmap)
        delta = cook_delta(cluster, new_hc, action.hostcomponentmap, old_hc)
    prepare_job(action, sub_action, job.id, obj, conf, delta, hosts, task.verbose)


def prepare_job(action, sub_action, job_id, obj, conf, delta, hosts, verbose):
    prepare_job_config(action, sub_action, job_id, obj, conf, verbose)
    inventory.prepare_job_inventory(obj, job_id, action, delta, hosts)
    prepare_ansible_config(job_id, action, sub_action)


def prepare_context(action, obj):
    obj_type = obj.prototype.type
    context = {'type': obj_type, f'{obj_type}_id': obj.id}
    if obj_type == 'service':
        context['cluster_id'] = obj.cluster.id
    elif obj_type == 'component':
        context['cluster_id'] = obj.cluster.id
        context['service_id'] = obj.service.id
    elif obj_type == 'host':
        if action.host_action:
            if action.prototype.type == 'component':
                component = ServiceComponent.obj.get(prototype=action.prototype)
                context['component_id'] = component.id
            if action.prototype.type == 'service':
                service = ClusterObject.obj.get(prototype=action.prototype)
                context['service_id'] = service.id
            if obj.cluster is not None:
                context['cluster_id'] = obj.cluster.id
        else:
            context['provider_id'] = obj.provider.id
    return context


def prepare_job_config(
    action, sub_action, job_id, obj, conf, verbose
):  # pylint: disable=too-many-branches,too-many-statements
    job_conf = {
        'adcm': {'config': get_adcm_config()},
        'context': prepare_context(action, obj),
        'env': {
            'run_dir': config.RUN_DIR,
            'log_dir': config.LOG_DIR,
            'tmp_dir': os.path.join(config.RUN_DIR, f'{job_id}', 'tmp'),
            'stack_dir': get_bundle_root(action) + '/' + action.prototype.bundle.hash,
            'status_api_token': config.STATUS_SECRET_KEY,
        },
        'job': {
            'id': job_id,
            'action': action.name,
            'job_name': action.name,
            'command': action.name,
            'script': action.script,
            'verbose': verbose,
            'playbook': cook_script(action, sub_action),
        },
    }
    if action.params:
        job_conf['job']['params'] = action.params

    if sub_action:
        job_conf['job']['script'] = sub_action.script
        job_conf['job']['job_name'] = sub_action.name
        job_conf['job']['command'] = sub_action.name
        if sub_action.params:
            job_conf['job']['params'] = sub_action.params

    cluster = get_object_cluster(obj)
    if cluster:
        job_conf['job']['cluster_id'] = cluster.id

    if action.prototype.type == 'service':
        if action.host_action:
            service = ClusterObject.obj.get(prototype=action.prototype, cluster=cluster)
            job_conf['job']['hostgroup'] = service.name
            job_conf['job']['service_id'] = service.id
            job_conf['job']['service_type_id'] = service.prototype.id
        else:
            job_conf['job']['hostgroup'] = obj.prototype.name
            job_conf['job']['service_id'] = obj.id
            job_conf['job']['service_type_id'] = obj.prototype.id
    elif action.prototype.type == 'component':
        if action.host_action:
            comp = ServiceComponent.obj.get(prototype=action.prototype, cluster=cluster)
            service = ClusterObject.obj.get(prototype=comp.prototype.parent, cluster=cluster)
            job_conf['job']['hostgroup'] = f'{service.name}.{comp.name}'
            job_conf['job']['service_id'] = service.id
            job_conf['job']['component_id'] = comp.id
            job_conf['job']['component_type_id'] = comp.prototype.id
        else:
            job_conf['job']['hostgroup'] = f'{obj.service.prototype.name}.{obj.prototype.name}'
            job_conf['job']['service_id'] = obj.service.id
            job_conf['job']['component_id'] = obj.id
            job_conf['job']['component_type_id'] = obj.prototype.id
    elif action.prototype.type == 'cluster':
        job_conf['job']['hostgroup'] = 'CLUSTER'
    elif action.prototype.type == 'host':
        job_conf['job']['hostgroup'] = 'HOST'
        job_conf['job']['hostname'] = obj.fqdn
        job_conf['job']['host_id'] = obj.id
        job_conf['job']['host_type_id'] = obj.prototype.id
        job_conf['job']['provider_id'] = obj.provider.id
    elif action.prototype.type == 'provider':
        job_conf['job']['hostgroup'] = 'PROVIDER'
        job_conf['job']['provider_id'] = obj.id
    elif action.prototype.type == 'adcm':
        job_conf['job']['hostgroup'] = '127.0.0.1'
    else:
        err('NOT_IMPLEMENTED', 'unknown prototype type "{}"'.format(action.prototype.type))

    if conf:
        job_conf['job']['config'] = conf

    fd = open(os.path.join(config.RUN_DIR, f'{job_id}/config.json'), 'w')
    json.dump(job_conf, fd, indent=3, sort_keys=True)
    fd.close()


def create_task(action, obj, conf, attr, hc, delta, hosts, event, verbose):
    task = create_one_job_task(action, obj, conf, attr, hc, hosts, event, verbose)
    for sub in SubAction.objects.filter(action=action):
        _job = create_job(action, sub, event, task)
    return task


def create_one_job_task(action, obj, conf, attr, hc, hosts, event, verbose):
    task = TaskLog(
        action=action,
        task_object=obj,
        config=conf,
        attr=attr,
        hostcomponentmap=hc,
        hosts=hosts,
        verbose=verbose,
        start_date=timezone.now(),
        finish_date=timezone.now(),
        status=config.Job.CREATED,
    )
    task.save()
    set_task_status(task, config.Job.CREATED, event)
    return task


def create_job(action, sub_action, event, task):
    job = JobLog(
        task=task,
        action=action,
        log_files=action.log_files,
        start_date=timezone.now(),
        finish_date=timezone.now(),
        status=config.Job.CREATED,
    )
    if sub_action:
        job.sub_action = sub_action
    job.save()
    LogStorage.objects.create(job=job, name='ansible', type='stdout', format='txt')
    LogStorage.objects.create(job=job, name='ansible', type='stderr', format='txt')
    set_job_status(job.id, config.Job.CREATED, event)
    os.makedirs(os.path.join(config.RUN_DIR, f'{job.id}', 'tmp'), exist_ok=True)
    return job


def get_state(action, job, status):
    sub_action = None
    if job and job.sub_action:
        sub_action = job.sub_action

    if status == config.Job.SUCCESS:
        if not action.state_on_success:
            log.warning('action "%s" success state is not set', action.name)
            state = None
        else:
            state = action.state_on_success
    elif status == config.Job.FAILED:
        if sub_action and sub_action.state_on_fail:
            state = sub_action.state_on_fail
        elif action.state_on_fail:
            state = action.state_on_fail
        else:
            log.warning('action "%s" fail state is not set', action.name)
            state = None
    else:
        log.error('unknown task status: %s', status)
        state = None
    return state


def set_action_state(action, task, obj, state):
    if not obj:
        log.warning('empty object for action %s of task #%s', action.name, task.id)
        return
    msg = 'action "%s" of task #%s will set %s state to "%s"'
    log.info(msg, action.name, task.id, obj_ref(obj), state)
    api.push_obj(obj, state)


def restore_hc(task, action, status):
    if status != config.Job.FAILED:
        return
    if not action.hostcomponentmap:
        return

    cluster = get_object_cluster(task.task_object)
    if cluster is None:
        log.error('no cluster in task #%s', task.id)
        return

    host_comp_list = []
    for hc in task.hostcomponentmap:
        host = Host.objects.get(id=hc['host_id'])
        service = ClusterObject.objects.get(id=hc['service_id'], cluster=cluster)
        comp = ServiceComponent.objects.get(id=hc['component_id'], cluster=cluster, service=service)
        host_comp_list.append((service, host, comp))

    log.warning('task #%s is failed, restore old hc', task.id)
    api.save_hc(cluster, host_comp_list)


def finish_task(task, job, status):
    action = task.action
    # GenericForeignKey does not work here (probably because of cashing)
    # obj = task.task_object
    model = get_model_by_type(task.action.prototype.type)
    # In case object was deleted from ansible plugin in job
    try:
        obj = model.objects.get(id=task.object_id)
    except model.DoesNotExist:
        obj = None
    state = get_state(action, job, status)
    event = Event()
    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())
        if state is not None:
            set_action_state(action, task, obj, state)
        unlock_objects(obj or get_object_cluster(obj), event)
        restore_hc(task, action, status)
        set_task_status(task, status, event)
    event.send_state()


def cook_log_name(tag, level, ext='txt'):
    return f'{tag}-{level}.{ext}'


def get_log(job):
    log_storage = LogStorage.objects.filter(job=job)
    logs = []

    for ls in log_storage:
        logs.append({'name': ls.name, 'type': ls.type, 'format': ls.format, 'id': ls.id})

    return logs


def log_group_check(group, fail_msg, success_msg):
    logs = CheckLog.objects.filter(group=group).values('result')
    result = all(log['result'] for log in logs)

    if result:
        msg = success_msg
    else:
        msg = fail_msg

    group.message = msg
    group.result = result
    group.save()


def log_check(job_id, group_data, check_data):
    job = JobLog.obj.get(id=job_id)
    if job.status != config.Job.RUNNING:
        err('JOB_NOT_FOUND', f'job #{job.id} has status "{job.status}", not "running"')

    group_title = group_data.pop('title')

    if group_title:
        group, _ = GroupCheckLog.objects.get_or_create(job=job, title=group_title)
    else:
        group = None

    check_data.update({'job': job, 'group': group})
    cl = CheckLog.objects.create(**check_data)

    if group is not None:
        group_data.update({'group': group})
        log_group_check(**group_data)

    ls, _ = LogStorage.objects.get_or_create(job=job, name='ansible', type='check', format='json')

    post_event(
        'add_job_log',
        'job',
        job_id,
        {
            'id': ls.id,
            'type': ls.type,
            'name': ls.name,
            'format': ls.format,
        },
    )
    return cl


def get_check_log(job_id):
    data = []
    group_subs = defaultdict(list)

    for cl in CheckLog.objects.filter(job_id=job_id):
        group = cl.group
        if group is None:
            data.append(
                {'title': cl.title, 'type': 'check', 'message': cl.message, 'result': cl.result}
            )
        else:
            if group not in group_subs:
                data.append(
                    {
                        'title': group.title,
                        'type': 'group',
                        'message': group.message,
                        'result': group.result,
                        'content': group_subs[group],
                    }
                )
            group_subs[group].append(
                {'title': cl.title, 'type': 'check', 'message': cl.message, 'result': cl.result}
            )
    return data


def finish_check(job_id):
    data = get_check_log(job_id)
    if not data:
        return

    job = JobLog.objects.get(id=job_id)
    LogStorage.objects.filter(job=job, name='ansible', type='check', format='json').update(
        body=json.dumps(data)
    )

    GroupCheckLog.objects.filter(job=job).delete()
    CheckLog.objects.filter(job=job).delete()


def log_custom(job_id, name, log_format, body):
    job = JobLog.obj.get(id=job_id)
    l1 = LogStorage.objects.create(job=job, name=name, type='custom', format=log_format, body=body)
    post_event(
        'add_job_log',
        'job',
        job_id,
        {
            'id': l1.id,
            'type': l1.type,
            'name': l1.name,
            'format': l1.format,
        },
    )


def check_all_status():
    err('NOT_IMPLEMENTED')


def run_task(task, event, args=''):
    err_file = open(os.path.join(config.LOG_DIR, 'task_runner.err'), 'a+')
    proc = subprocess.Popen(
        [os.path.join(config.CODE_DIR, 'task_runner.py'), str(task.id), args], stderr=err_file
    )
    log.info("run task #%s, python process %s", task.id, proc.pid)
    task.pid = proc.pid

    set_task_status(task, config.Job.RUNNING, event)


@background(schedule=1)
def log_rotation():
    log.info('Run log rotation')
    adcm_object = ADCM.objects.get(id=1)
    cl = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    adcm_conf = cl.config

    log_rotation_on_db = adcm_conf['job_log']['log_rotation_in_db']
    log_rotation_on_fs = adcm_conf['job_log']['log_rotation_on_fs']

    if log_rotation_on_db:
        rotation_jobs_on_db = JobLog.objects.filter(
            finish_date__lt=timezone.now() - timedelta(days=log_rotation_on_db)
        )
        if rotation_jobs_on_db:
            task_ids = [job['task_id'] for job in rotation_jobs_on_db.values('task_id')]
            with transaction.atomic():
                rotation_jobs_on_db.delete()
                TaskLog.objects.filter(id__in=task_ids).delete()

            log.info('rotation log from db')

    if log_rotation_on_fs:  # pylint: disable=too-many-nested-blocks
        for name in os.listdir(config.RUN_DIR):
            if not name.startswith('.'):  # a line of code is used for development
                path = os.path.join(config.RUN_DIR, name)
                try:
                    m_time = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
                    if timezone.now() - m_time > timedelta(days=log_rotation_on_fs):
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                except FileNotFoundError:
                    pass

        log.info('rotation log from fs')


def prepare_ansible_config(job_id, action, sub_action):
    config_parser = ConfigParser()
    config_parser['defaults'] = {
        'stdout_callback': 'yaml',
        'callback_whitelist': 'profile_tasks',
    }
    adcm_object = ADCM.objects.get(id=1)
    cl = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    adcm_conf = cl.config
    mitogen = adcm_conf['ansible_settings']['mitogen']
    if mitogen:
        config_parser['defaults']['strategy'] = 'mitogen_linear'
        config_parser['defaults']['strategy_plugins'] = os.path.join(
            config.PYTHON_SITE_PACKAGES, 'ansible_mitogen/plugins/strategy'
        )
        config_parser['defaults']['host_key_checking'] = 'False'
    forks = adcm_conf['ansible_settings']['forks']
    config_parser['defaults']['forks'] = str(forks)
    params = action.params
    if sub_action:
        params = sub_action.params

    if 'jinja2_native' in params:
        config_parser['defaults']['jinja2_native'] = str(params['jinja2_native'])

    with open(os.path.join(config.RUN_DIR, f'{job_id}/ansible.cfg'), 'w') as config_file:
        config_parser.write(config_file)


def set_task_status(task, status, event):
    task.status = status
    task.finish_date = timezone.now()
    task.save()
    event.set_task_status(task.id, status)


def set_job_status(job_id, status, event, pid=0):
    JobLog.objects.filter(id=job_id).update(status=status, pid=pid, finish_date=timezone.now())
    event.set_job_status(job_id, status)


def abort_all(event):
    for task in TaskLog.objects.filter(status=config.Job.RUNNING):
        set_task_status(task, config.Job.ABORTED, event)
    for job in JobLog.objects.filter(status=config.Job.RUNNING):
        set_job_status(job.id, config.Job.ABORTED, event)
