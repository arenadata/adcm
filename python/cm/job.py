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
# pylint: disable=too-many-branches

import json
import os
import re
import signal
import subprocess
import time
import shutil
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from background_task import background

import cm.config as config
from cm import api, issue, inventory, adcm_config
from cm.adcm_config import obj_ref, process_file_type, process_config
from cm.errors import raise_AdcmEx as err
from cm.inventory import get_obj_config
from cm.logger import log
from cm.status_api import Event
from cm.models import (
    Cluster, Action, SubAction, TaskLog, JobLog, CheckLog, Host, ADCM,
    ClusterObject, HostComponent, ServiceComponent, HostProvider, DummyData,
    LogStorage, ConfigLog, GroupCheckLog
)


def start_task(action_id, selector, conf, hc, hosts):   # pylint: disable=too-many-locals
    try:
        action = Action.objects.get(id=action_id)
    except Action.DoesNotExist:
        err('ACTION_NOT_FOUND')

    obj, cluster, provider = check_task(action, selector, conf)
    act_conf, spec = check_action_config(action, conf)
    host_map, delta = check_hostcomponentmap(cluster, action, hc)
    check_action_hosts(action, cluster, provider, hosts)
    old_hc = get_hc(cluster)

    if action.type not in ['task', 'job']:
        msg = f'unknown type "{action.type}" for action: {action}, {action.context}: {obj.name}'
        err('WRONG_ACTION_TYPE', msg)
    event = Event()
    with transaction.atomic():
        task = lock_create_task(
            action, obj, selector, act_conf, spec, old_hc, delta, host_map, cluster, hosts, event
        )

    event.send_state()
    run_task(task, event)
    event.send_state()

    log_rotation()

    return task


def check_task(action, selector, conf):
    obj, cluster, provider = get_action_context(action, selector)
    check_action_state(action, obj)
    iss = issue.get_issue(obj)
    if not issue.issue_to_bool(iss):
        err('TASK_ERROR', 'action has issues', iss)
    return obj, cluster, provider


def check_action_hosts(action, cluster, provider, hosts):
    if not hosts:
        return
    if not action.partial_execution:
        err('TASK_ERROR', 'Only action with partial_execution permission can receive host list')
    if not isinstance(hosts, list):
        err('TASK_ERROR', 'Hosts should be array')
    for host_id in hosts:
        if not isinstance(host_id, int):
            err('TASK_ERROR', f'host id should be integer ({host_id})')
        try:
            host = Host.objects.get(id=host_id)
        except Host.DoesNotExist:
            err('TASK_ERROR', f'Can not find host with id #{host_id}')
        if cluster and host.cluster != cluster:
            err('TASK_ERROR', f'host #{host_id} does not belong to cluster #{cluster.id}')
        if provider and host.provider != provider:
            err('TASK_ERROR', f'host #{host_id} does not belong to host provider #{provider.id}')


def lock_create_task(action, obj, selector, conf, spec, old_hc, delta, host_map, cluster, hosts,
                     event):
    lock_objects(obj, event)

    if host_map:
        api.save_hc(cluster, host_map)

    if action.type == 'task':
        task = create_task(action, selector, obj, conf, old_hc, delta, hosts, event)
        new_conf = process_config(task, spec, conf)
    else:
        task = create_one_job_task(action.id, selector, obj, conf, old_hc, hosts, event)
        job = create_job(action, None, selector, event, task.id)
        new_conf = process_config(task, spec, conf)
        prepare_job(action, None, selector, job.id, obj, new_conf, delta, hosts)

    if conf:
        process_file_type(task, spec, conf)
        task.config = json.dumps(new_conf)
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
        config.Job.SUCCESS: ('TASK_IS_SUCCESS', f'task #{task.id} is success')

    }
    action = Action.objects.get(id=task.action_id)
    if not action.allow_to_terminate:
        err('NOT_ALLOWED_TERMINATION',
            f'not allowed termination task #{task.id} for action #{action.id}')
    if task.status in [config.Job.FAILED, config.Job.ABORTED, config.Job.SUCCESS]:
        err(*errors.get(task.status))
    i = 0
    while not JobLog.objects.filter(task_id=task.id, status=config.Job.RUNNING) and i < 10:
        time.sleep(0.5)
        i += 1
    if i == 10:
        err('NO_JOBS_RUNNING', 'no jobs running')
    os.kill(task.pid, signal.SIGTERM)


def get_action_context(action, selector):
    cluster = None
    provider = None
    if action.prototype.type == 'service':
        check_selector(selector, 'cluster')
        obj = check_service_task(selector['cluster'], action)
        cluster = obj.cluster
    elif action.prototype.type == 'host':
        check_selector(selector, 'host')
        obj = check_host(selector['host'], selector)
        cluster = obj.cluster
    elif action.prototype.type == 'cluster':
        check_selector(selector, 'cluster')
        obj = check_cluster(selector['cluster'])
        cluster = obj
    elif action.prototype.type == 'provider':
        check_selector(selector, 'provider')
        obj = check_provider(selector['provider'])
        provider = obj
    elif action.prototype.type == 'adcm':
        check_selector(selector, 'adcm')
        obj = check_adcm(selector['adcm'])
    else:
        err('WRONG_ACTION_CONTEXT', f'unknown action context "{action.prototype.type}"')
    return obj, cluster, provider


def check_action_state(action, obj):
    if obj.state == config.Job.LOCKED:
        err('TASK_ERROR', 'object is locked')
    if action.state_available == '':
        err('TASK_ERROR', 'action is disabled')
    available = json.loads(action.state_available)
    if available == 'any':
        return
    if obj.state in available:
        return
    err('TASK_ERROR', 'action is disabled')


def lock_obj(obj, event):
    if obj.stack:
        stack = json.loads(obj.stack)
    else:
        stack = []

    if not stack:
        stack = [obj.state]
    elif stack[-1] != obj.state:
        stack.append(obj.state)

    log.debug('lock %s, stack: %s', obj_ref(obj), stack)
    obj.stack = json.dumps(stack)
    api.set_object_state(obj, config.Job.LOCKED, event)


def unlock_obj(obj, event):
    if obj.stack:
        stack = json.loads(obj.stack)
    else:
        log.warning('no stack in %s for unlock', obj_ref(obj))
        return
    try:
        state = stack.pop()
    except IndexError:
        log.warning('empty stack in %s for unlock', obj_ref(obj))
        return
    log.debug('unlock %s, stack: %s', obj_ref(obj), stack)
    obj.stack = json.dumps(stack)
    api.set_object_state(obj, state, event)


def lock_objects(obj, event):
    if isinstance(obj, ClusterObject):
        lock_obj(obj, event)
        lock_obj(obj.cluster, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            lock_obj(host, event)
    elif isinstance(obj, Host):
        lock_obj(obj, event)
        if obj.cluster:
            lock_obj(obj.cluster, event)
            for service in ClusterObject.objects.filter(cluster=obj.cluster):
                lock_obj(service, event)
    elif isinstance(obj, HostProvider):
        lock_obj(obj, event)
        for host in Host.objects.filter(provider=obj):
            lock_obj(host, event)
    elif isinstance(obj, ADCM):
        lock_obj(obj, event)
    elif isinstance(obj, Cluster):
        lock_obj(obj, event)
        for service in ClusterObject.objects.filter(cluster=obj):
            lock_obj(service, event)
        for host in Host.objects.filter(cluster=obj):
            lock_obj(host, event)
    else:
        log.warning('lock_objects: unknown object type: %s', obj)


def unlock_objects(obj, event):
    if isinstance(obj, ClusterObject):
        unlock_obj(obj, event)
        unlock_obj(obj.cluster, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            unlock_obj(host, event)
    elif isinstance(obj, Host):
        unlock_obj(obj, event)
        if obj.cluster:
            unlock_obj(obj.cluster, event)
            for service in ClusterObject.objects.filter(cluster=obj.cluster):
                unlock_obj(service, event)
    elif isinstance(obj, HostProvider):
        unlock_obj(obj, event)
        for host in Host.objects.filter(provider=obj):
            unlock_obj(host, event)
    elif isinstance(obj, ADCM):
        unlock_obj(obj, event)
    elif isinstance(obj, Cluster):
        unlock_obj(obj, event)
        for service in ClusterObject.objects.filter(cluster=obj):
            unlock_obj(service, event)
        for host in Host.objects.filter(cluster=obj):
            unlock_obj(host, event)
    else:
        log.warning('unlock_objects: unknown object type: %s', obj)


def unlock_all(event):
    for obj in Cluster.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj, event)
    for obj in HostProvider.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj, event)
    for obj in ClusterObject.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj, event)
    for obj in Host.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj, event)
    for task in TaskLog.objects.filter(status=config.Job.RUNNING):
        set_task_status(task, config.Job.ABORTED, event)
    for job in JobLog.objects.filter(status=config.Job.RUNNING):
        set_job_status(job.id, config.Job.ABORTED, event)


def check_action_config(action, conf):
    spec, flat_spec, _, _ = adcm_config.get_prototype_config(action.prototype, action)
    if spec:
        if not conf:
            err('TASK_ERROR', 'action config is required')
    else:
        return None, None
    return adcm_config.check_config_spec(action.prototype, action, spec, flat_spec, conf), spec


def add_to_dict(my_dict, key, subkey, value):
    if key not in my_dict:
        my_dict[key] = {}
    my_dict[key][subkey] = value


def get_hc(cluster):
    if not cluster:
        return None
    hc_map = []
    for hc in HostComponent.objects.filter(cluster=cluster):
        hc_map.append({
            'host_id': hc.host.id,
            'service_id': hc.service.id,
            'component_id': hc.component.id,
        })
    return hc_map


def check_action_hc(action_hc, service, component, action):
    for item in action_hc:
        if item['service'] == service and item['component'] == component:
            if item['action'] == action:
                return True
    return False


def cook_comp_key(name, subname):
    return f'{name}.{subname}'


def cook_delta(cluster, new_hc, action_hc, old=None):
    def add_delta(delta, action, key, fqdn, host):
        service, comp = key.split('.')
        if not check_action_hc(action_hc, service, comp, action):
            msg = (f'no permission to "{action}" component "{comp}" of '
                   f'service "{service}" to/from hostcomponentmap')
            err('WRONG_ACTION_HC', msg)
        add_to_dict(delta[action], key, fqdn, host)

    new = {}
    for service, host, comp in new_hc:
        key = cook_comp_key(service.prototype.name, comp.component.name)
        add_to_dict(new, key, host.fqdn, host)

    if not old:
        old = {}
        for hc in HostComponent.objects.filter(cluster=cluster):
            key = cook_comp_key(hc.service.prototype.name, hc.component.component.name)
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
    return hostmap, cook_delta(cluster, hostmap, json.loads(action.hostcomponentmap))


def check_selector(selector, key):
    if key not in selector:
        err('WRONG_SELECTOR', f'selector must contains "{key}" field')
    return selector[key]


def check_service_task(cluster_id, action):
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        try:
            service = ClusterObject.objects.get(cluster=cluster, prototype=action.prototype)
            return service
        except ClusterObject.DoesNotExist:
            msg = (f'service #{action.prototype.id} for action '
                   f'"{action.name}" is not installed in cluster #{cluster.id}')
            err('CLUSTER_SERVICE_NOT_FOUND', msg)
    except Cluster.DoesNotExist:
        err('CLUSTER_NOT_FOUND')


def check_cluster(cluster_id):
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        return cluster
    except Cluster.DoesNotExist:
        err('CLUSTER_NOT_FOUND')


def check_provider(provider_id):
    try:
        provider = HostProvider.objects.get(id=provider_id)
        return provider
    except HostProvider.DoesNotExist:
        err('PROVIDER_NOT_FOUND')


def check_adcm(adcm_id):
    try:
        adcm = ADCM.objects.get(id=adcm_id)
        return adcm
    except ADCM.DoesNotExist:
        err('ADCM_NOT_FOUND')


def check_host(host_id, selector):
    try:
        host = Host.objects.get(id=host_id)
        if 'cluster' in selector:
            if not host.cluster:
                msg = f'Host #{host_id} does not belong to any cluster'
                err('HOST_NOT_FOUND', msg)
            if host.cluster.id != selector['cluster']:
                msg = f'Host #{host_id} does not belong to cluster #{selector["cluster"]}'
                err('HOST_NOT_FOUND', msg)
        return host
    except Host.DoesNotExist:
        err('HOST_NOT_FOUND')


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
    try:
        adcm = ADCM.objects.get()
        return get_obj_config(adcm)
    except ADCM.DoesNotExist:
        return {}


def get_new_hc(cluster):
    new_hc = []
    for hc in HostComponent.objects.filter(cluster=cluster):
        new_hc.append((hc.service, hc.host, hc.component))
    return new_hc


def get_old_hc(saved_hc):
    if not saved_hc:
        return {}
    old_hc = {}
    for hc in json.loads(saved_hc):
        service = ClusterObject.objects.get(id=hc['service_id'])
        comp = ServiceComponent.objects.get(id=hc['component_id'])
        host = Host.objects.get(id=hc['host_id'])
        key = cook_comp_key(service.prototype.name, comp.component.name)
        add_to_dict(old_hc, key, host.fqdn, host)
    return old_hc


def re_prepare_job(task, job):
    conf = None
    hosts = None
    delta = {}
    if task.config:
        conf = json.loads(task.config)
    if task.hosts:
        hosts = json.loads(task.hosts)
    selector = json.loads(task.selector)
    action = Action.objects.get(id=task.action_id)
    obj, cluster, _provider = get_action_context(action, selector)
    sub_action = None
    if job.sub_action_id:
        sub_action = SubAction.objects.get(id=job.sub_action_id)
    if action.hostcomponentmap:
        new_hc = get_new_hc(cluster)
        old_hc = get_old_hc(task.hostcomponentmap)
        delta = cook_delta(cluster, new_hc, json.loads(action.hostcomponentmap), old_hc)
    prepare_job(action, sub_action, selector, job.id, obj, conf, delta, hosts)


def prepare_job(action, sub_action, selector, job_id, obj, conf, delta, hosts):
    prepare_job_config(action, sub_action, selector, job_id, obj, conf)
    inventory.prepare_job_inventory(selector, job_id, delta, hosts)


def prepare_context(selector):
    context = {}
    if 'cluster' in selector:
        context['type'] = 'cluster'
        context['cluster_id'] = selector['cluster']
    if 'service' in selector:
        context['type'] = 'service'
        context['service_id'] = selector['service']
    if 'provider' in selector:
        context['type'] = 'provider'
        context['provider_id'] = selector['provider']
    if 'host' in selector:
        context['type'] = 'host'
        context['host_id'] = selector['host']
    if 'adcm' in selector:
        context['type'] = 'adcm'
        context['adcm_id'] = selector['adcm']
    return context


def prepare_job_config(action, sub_action, selector, job_id, obj, conf):
    job_conf = {
        'adcm': {'config': get_adcm_config()},
        'context': prepare_context(selector),
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
            'playbook': cook_script(action, sub_action)
        },
    }
    if action.params:
        job_conf['job']['params'] = json.loads(action.params)

    if sub_action:
        job_conf['job']['script'] = sub_action.script
        job_conf['job']['job_name'] = sub_action.name
        job_conf['job']['command'] = sub_action.name
        if sub_action.params:
            job_conf['job']['params'] = json.loads(sub_action.params)

    if 'cluster' in selector:
        job_conf['job']['cluster_id'] = selector['cluster']

    if action.prototype.type == 'service':
        job_conf['job']['hostgroup'] = obj.prototype.name
        job_conf['job']['service_id'] = obj.id
        job_conf['job']['service_type_id'] = obj.prototype.id
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


def create_task(action, selector, obj, conf, hc, delta, hosts, event):
    task = TaskLog(
        action_id=action.id,
        object_id=obj.id,
        selector=json.dumps(selector),
        config=json.dumps(conf),
        hostcomponentmap=json.dumps(hc),
        hosts=json.dumps(hosts),
        start_date=timezone.now(),
        finish_date=timezone.now(),
        status=config.Job.CREATED,
    )
    task.save()
    set_task_status(task, config.Job.CREATED, event)
    for sub in SubAction.objects.filter(action=action):
        job = create_job(action, sub, selector, event, task.id)
        prepare_job(action, sub, selector, job.id, obj, conf, delta, hosts)
    return task


def create_one_job_task(action_id, selector, obj, conf, hc, hosts, event):
    task = TaskLog(
        action_id=action_id,
        object_id=obj.id,
        selector=json.dumps(selector),
        config=json.dumps(conf),
        hostcomponentmap=json.dumps(hc),
        hosts=json.dumps(hosts),
        start_date=timezone.now(),
        finish_date=timezone.now(),
        status=config.Job.CREATED,
    )
    task.save()
    set_task_status(task, config.Job.CREATED, event)
    return task


def create_job(action, sub_action, selector, event, task_id=0):
    job = JobLog(
        task_id=task_id,
        action_id=action.id,
        selector=json.dumps(selector),
        log_files=action.log_files,
        start_date=timezone.now(),
        finish_date=timezone.now(),
        status=config.Job.CREATED
    )
    if sub_action:
        job.sub_action_id = sub_action.id
    job.save()
    LogStorage.objects.create(job=job, name='ansible', type='stdout', format='txt')
    LogStorage.objects.create(job=job, name='ansible', type='stderr', format='txt')
    set_job_status(job.id, config.Job.CREATED, event)
    os.makedirs(os.path.join(config.RUN_DIR, f'{job.id}', 'tmp'), exist_ok=True)
    return job


def set_job_status(job_id, status, event, pid=0):
    JobLog.objects.filter(id=job_id).update(status=status, pid=pid, finish_date=timezone.now())
    event.set_job_status(job_id, status)


def set_task_status(task, status, event):
    task.status = status
    task.finish_date = timezone.now()
    task.save()
    event.set_task_status(task.id, status)


def get_task_obj(context, obj_id):
    def get_obj_safe(model, obj_id):
        try:
            return model.objects.get(id=obj_id)
        except model.DoesNotExist:
            return None

    if context == 'service':
        obj = get_obj_safe(ClusterObject, obj_id)
    elif context == 'host':
        obj = get_obj_safe(Host, obj_id)
    elif context == 'cluster':
        obj = Cluster.objects.get(id=obj_id)
    elif context == 'provider':
        obj = HostProvider.objects.get(id=obj_id)
    elif context == 'adcm':
        obj = ADCM.objects.get(id=obj_id)
    else:
        log.error("unknown context: %s", context)
        return None
    return obj


def get_state(action, job, status):
    sub_action = None
    if job and job.sub_action_id:
        sub_action = SubAction.objects.get(id=job.sub_action_id)

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

    selector = json.loads(task.selector)
    if 'cluster' not in selector:
        log.error('no cluster in task #%s selector', task.id)
        return
    cluster = Cluster.objects.get(id=selector['cluster'])

    host_comp_list = []
    for hc in json.loads(task.hostcomponentmap):
        host = Host.objects.get(id=hc['host_id'])
        service = ClusterObject.objects.get(id=hc['service_id'], cluster=cluster)
        comp = ServiceComponent.objects.get(id=hc['component_id'], cluster=cluster, service=service)
        host_comp_list.append((service, host, comp))

    log.warning('task #%s is failed, restore old hc', task.id)
    api.save_hc(cluster, host_comp_list)


def finish_task(task, job, status):
    action = Action.objects.get(id=task.action_id)
    obj = get_task_obj(action.prototype.type, task.object_id)
    state = get_state(action, job, status)
    event = Event()
    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())
        if state is not None:
            set_action_state(action, task, obj, state)
        unlock_objects(obj, event)
        restore_hc(task, action, status)
        set_task_status(task, status, event)
    event.send_state()


def cook_log_name(tag, level, ext='txt'):
    return f'{tag}-{level}.{ext}'


def read_log(job_id, tag, level, log_type):
    fname = os.path.join(config.RUN_DIR, f'{job_id}/{tag}-{level}.{log_type}')
    try:
        f = open(fname, 'r')
        data = f.read()
        f.close()
        return data
    except FileNotFoundError:
        err('LOG_NOT_FOUND', 'no log file {}'.format(fname))


def get_host_log_files(job_id, tag):
    logs = []
    p = re.compile('^' + str(job_id) + '-' + tag + r'-(out|err)\.(txt|json)$')
    for item in os.listdir(config.LOG_DIR):
        m = p.findall(item)
        if m:
            (level, ext) = m[0]
            logs.append((level, ext, item))
    return logs


def get_log(job):
    log_storage = LogStorage.objects.filter(job=job)
    logs = []

    for ls in log_storage:
        logs.append({
            'name': ls.name,
            'type': ls.type,
            'format': ls.format,
            'id': ls.id
        })

    return logs


def get_log_files(job):
    logs = []
    for level in ['out', 'err']:
        logs.append({
            'level': level,
            'tag': 'ansible',
            'type': 'txt',
            'file': cook_log_name(job.id, 'ansible', level)
        })
    if job.log_files == '':
        return logs
    for tag in json.loads(job.log_files):
        for (level, ext, file) in get_host_log_files(job.id, tag):
            logs.append({
                'level': level,
                'tag': tag,
                'type': ext,
                'file': file
            })
    return logs


def log_check(job_id, title, res, msg, group):
    try:
        job = JobLog.objects.get(id=job_id)
        if job.status != config.Job.RUNNING:
            err('JOB_NOT_FOUND', f'job #{job.id} has status "{job.status}", not "running"')
    except JobLog.DoesNotExist:
        err('JOB_NOT_FOUND', f'no job with id #{job_id}')
    cl = CheckLog(job_id=job.id, title=title, message=msg, result=res, group=group)
    try:
        LogStorage.objects.get(job=job, name='check', type='check')
    except LogStorage.DoesNotExist:
        LogStorage.objects.create(job=job, name='check', type='check', format='json')
    cl.save()
    return cl


def create_group_log(job_id, title):
    group, _ = GroupCheckLog.objects.get_or_create(job_id=job_id, title=title)
    return group


def log_group_check(group, fail_msg, success_msg):
    logs = CheckLog.objects.filter(group=group).values('result')
    result = all([log['result'] for log in logs])

    if result:
        msg = success_msg
    else:
        msg = fail_msg

    group.message = msg
    group.result = result
    group.save()


def finish_check(job_id):
    try:
        groups = GroupCheckLog.objects.filter(job_id=job_id)
    except GroupCheckLog.DoesNotExist:
        groups = []

    data = []
    for group in groups:
        data_group = {'title': group.title, 'type': 'group', 'result': group.result,
                      'msg': group.message, 'subs': []}
        for cl in CheckLog.objects.filter(job_id=int(job_id), group=group):
            data_group['subs'].append(
                {'title': cl.title, 'type': 'check', 'message': cl.message, 'result': cl.result})
        data.append(data_group)

    if not data:
        return

    for cl in CheckLog.objects.filter(job_id=job_id, group=None):
        data.append(
            {'title': cl.title, 'type': 'check', 'message': cl.message, 'result': cl.result})

    job = JobLog.objects.get(id=job_id)
    LogStorage.objects.filter(job=job, name='check', type='check', format='json').update(
        body=json.dumps(data))

    GroupCheckLog.objects.filter(job_id=job_id).delete()
    CheckLog.objects.filter(job_id=job_id).delete()


def log_custom(job_id, name, log_format, body):
    try:
        job = JobLog.objects.get(id=job_id)
        LogStorage.objects.create(job=job, name=name, type='custom', format=log_format, body=body)
    except JobLog.DoesNotExist:
        err('JOB_NOT_FOUND', f'no job with id #{job_id}')


def check_all_status():
    err('NOT_IMPLEMENTED')


def run_task(task, event, args=''):
    err_file = open(os.path.join(config.LOG_DIR, 'task_runner.err'), 'a+')
    proc = subprocess.Popen([
        os.path.join(config.CODE_DIR, 'task_runner.py'),
        str(task.id),
        args
    ], stderr=err_file)
    log.info("run task #%s, python process %s", task.id, proc.pid)
    task.pid = proc.pid

    set_task_status(task, config.Job.RUNNING, event)


@background(schedule=1)
def log_rotation():
    log.info('Run log rotation')
    adcm_object = ADCM.objects.get(id=1)
    config_logs = ConfigLog.objects.filter(obj_ref=adcm_object.config)
    adcm_conf = {}
    for config_log in config_logs:
        adcm_conf.update(json.loads(config_log.config))
    log_rotation_on_db = adcm_conf['job_log']['log_rotation_in_db']
    log_rotation_on_fs = adcm_conf['job_log']['log_rotation_on_fs']

    if log_rotation_on_db:
        rotation_jobs_on_db = JobLog.objects.filter(
            finish_date__lt=timezone.now() - timedelta(days=log_rotation_on_db))
        if rotation_jobs_on_db:
            task_ids = [job['task_id'] for job in rotation_jobs_on_db.values('task_id')]
            rotation_jobs_on_db.delete()
            TaskLog.objects.filter(id__in=task_ids).delete()

            log.info('rotation log from db')

    if log_rotation_on_fs:
        rotation_jobs_on_fs = JobLog.objects.filter(
            finish_date__lt=timezone.now() - timedelta(days=log_rotation_on_fs)).values('id')

        if rotation_jobs_on_fs:

            for job in rotation_jobs_on_fs:
                shutil.rmtree(os.path.join(config.RUN_DIR, str(job['id'])))
            log.info('rotation log from fs')
