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

import json
import os
import re
import signal
import subprocess

from django.db import transaction
from django.utils import timezone

import cm.config as config
from cm import api, status_api, issue, inventory, adcm_config
from cm.adcm_config import obj_ref
from cm.errors import raise_AdcmEx as err
from cm.inventory import get_obj_config
from cm.logger import log
from cm.models import (Cluster, Action, SubAction, TaskLog, JobLog, Host, ADCM,
                       ClusterObject, HostComponent, ServiceComponent, HostProvider)


def start_task(action_id, selector, conf, hc):
    try:
        action = Action.objects.get(id=action_id)
    except Action.DoesNotExist:
        err('ACTION_NOT_FOUND')

    obj, act_conf, old_hc, delta, host_map, cluster = get_data_for_task(action, selector, conf, hc)

    if action.type not in ['task', 'job']:
        msg = f'unknown type "{action.type}" for action: {action}, {action.context}: {obj.name}'
        err('WRONG_ACTION_TYPE', msg)

    with transaction.atomic():
        task = lock_create_task(action, obj, selector, act_conf, old_hc, delta, host_map, cluster)
    run_task(task)

    return task


def get_data_for_task(action, selector, conf, hc):
    obj, cluster = get_action_context(action, selector)
    check_action_state(action, obj)
    iss = issue.get_issue(obj)
    if not issue.issue_to_bool(iss):
        err('TASK_ERROR', 'action has issues', iss)
    act_conf = check_action_config(action, conf)
    host_map, delta = check_hostcomponentmap(cluster, action, hc)
    old_hc = get_hc(cluster)
    return obj, act_conf, old_hc, delta, host_map, cluster


def lock_create_task(action, obj, selector, act_conf, old_hc, delta, host_map, cluster):  # pylint: disable=too-many-arguments
    lock_objects(obj)

    if host_map:
        api.save_hc(cluster, host_map)

    if action.type == 'task':
        task = create_task(action, selector, obj, act_conf, old_hc, delta)
    else:
        task = create_one_job_task(action.id, selector, obj, act_conf, old_hc)
        job = create_job(action, None, selector, task.id)
        prepare_job(action, None, selector, job.id, obj, act_conf, delta)

    return task


def restart_task(task):
    if task.status in (config.Job.CREATED, config.Job.RUNNING):
        err('TASK_ERROR', f'task #{task.id} is running')
    elif task.status == config.Job.SUCCESS:
        run_task(task)
    elif task.status in (config.Job.FAILED, config.Job.ABORTED):
        run_task(task, 'restart')
    else:
        err('TASK_ERROR', f'task #{task.id} has unexpected status: {task.status}')


def cancel_task(task):
    if task.status == config.Job.RUNNING:
        running_jobs = JobLog.objects.filter(task_id=task.id, status='running')
        for job in running_jobs:
            os.kill(job.pid, signal.SIGTERM)
    else:
        err('TASK_ERROR', f'task #{task.id} is {task.status}')


def get_action_context(action, selector):
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
        cluster = None
    elif action.prototype.type == 'adcm':
        check_selector(selector, 'adcm')
        obj = check_adcm(selector['adcm'])
        cluster = None
    else:
        err('WRONG_ACTION_CONTEXT', f'unknown action context "{action.prototype.type}"')
    return obj, cluster


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


def lock_obj(obj):
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
    api.set_object_state(obj, config.Job.LOCKED)


def unlock_obj(obj):
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
    api.set_object_state(obj, state)


def lock_objects(obj):
    if isinstance(obj, ClusterObject):
        lock_obj(obj)
        lock_obj(obj.cluster)
        for host in Host.objects.filter(cluster=obj.cluster):
            lock_obj(host)
    elif isinstance(obj, Host):
        lock_obj(obj)
        if obj.cluster:
            lock_obj(obj.cluster)
            for service in ClusterObject.objects.filter(cluster=obj.cluster):
                lock_obj(service)
    elif isinstance(obj, HostProvider):
        lock_obj(obj)
    elif isinstance(obj, ADCM):
        lock_obj(obj)
    elif isinstance(obj, Cluster):
        lock_obj(obj)
        for service in ClusterObject.objects.filter(cluster=obj):
            lock_obj(service)
        for host in Host.objects.filter(cluster=obj):
            lock_obj(host)
    else:
        log.warning('lock_objects: unknown object type: %s', obj)


def unlock_objects(obj):
    if isinstance(obj, ClusterObject):
        unlock_obj(obj)
        unlock_obj(obj.cluster)
        for host in Host.objects.filter(cluster=obj.cluster):
            unlock_obj(host)
    elif isinstance(obj, Host):
        unlock_obj(obj)
        if obj.cluster:
            unlock_obj(obj.cluster)
            for service in ClusterObject.objects.filter(cluster=obj.cluster):
                unlock_obj(service)
    elif isinstance(obj, HostProvider):
        unlock_obj(obj)
    elif isinstance(obj, ADCM):
        unlock_obj(obj)
    elif isinstance(obj, Cluster):
        unlock_obj(obj)
        for service in ClusterObject.objects.filter(cluster=obj):
            unlock_obj(service)
        for host in Host.objects.filter(cluster=obj):
            unlock_obj(host)
    else:
        log.warning('unlock_objects: unknown object type: %s', obj)


def unlock_all():
    for obj in Cluster.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj)
    for obj in HostProvider.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj)
    for obj in ClusterObject.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj)
    for obj in Host.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj)
    for task in TaskLog.objects.filter(status=config.Job.RUNNING):
        set_task_status(task, config.Job.ABORTED)
    for job in JobLog.objects.filter(status=config.Job.RUNNING):
        set_job_status(job.id, config.Job.ABORTED)


def check_action_config(action, conf):
    spec, flat_spec, _, _ = adcm_config.get_prototype_config(action.prototype, action)
    if spec:
        if not conf:
            err('TASK_ERROR', 'action config is required')
    else:
        return None
    return adcm_config.check_config_spec(action.prototype, action, spec, flat_spec, conf)


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


def cook_delta(cluster, new_hc, action_hc, old=None):  # pylint: disable=too-many-branches
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
    delta = {}
    if task.config:
        conf = json.loads(task.config)
    selector = json.loads(task.selector)
    action = Action.objects.get(id=task.action_id)
    obj, cluster = get_action_context(action, selector)
    sub_action = None
    if job.sub_action_id:
        sub_action = SubAction.objects.get(id=job.sub_action_id)
    if action.hostcomponentmap:
        new_hc = get_new_hc(cluster)
        old_hc = get_old_hc(task.hostcomponentmap)
        delta = cook_delta(cluster, new_hc, json.loads(action.hostcomponentmap), old_hc)
    prepare_job(action, sub_action, selector, job.id, obj, conf, delta)


def prepare_job(action, sub_action, selector, job_id, obj, conf, delta):
    prepare_job_config(action, sub_action, selector, job_id, obj, conf)
    inventory.prepare_job_inventory(selector, job_id, delta)


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
        'adcm': {
            'config': get_adcm_config()
        },
        'context': prepare_context(selector),
        'env': {
            'run_dir': config.RUN_DIR,
            'log_dir': config.LOG_DIR,
            'stack_dir': get_bundle_root(action) + '/' + action.prototype.bundle.hash,
            'status_api_token': config.STATUS_SECRET_KEY,
        },
        'job': {
            'id': job_id,
            'command': action.name,
            'script': action.script,
            'playbook': cook_script(action, sub_action)
        },
    }
    if action.params:
        job_conf['job']['params'] = json.loads(action.params)

    if sub_action:
        job_conf['job']['script'] = sub_action.script
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

    fd = open('{}/{}-config.json'.format(config.RUN_DIR, job_id), 'w')
    json.dump(job_conf, fd, indent=3, sort_keys=True)
    fd.close()


def create_task(action, selector, obj, conf, hc, delta):
    task = TaskLog(
        action_id=action.id,
        object_id=obj.id,
        selector=json.dumps(selector),
        config=json.dumps(conf),
        hostcomponentmap=json.dumps(hc),
        start_date=timezone.now(),
        finish_date=timezone.now(),
        status=config.Job.CREATED,
    )
    task.save()
    set_task_status(task, config.Job.CREATED)
    for sub in SubAction.objects.filter(action=action):
        job = create_job(action, sub, selector, task.id)
        prepare_job(action, sub, selector, job.id, obj, conf, delta)
    return task


def create_one_job_task(action_id, selector, obj, conf, hc):
    task = TaskLog(
        action_id=action_id,
        object_id=obj.id,
        selector=json.dumps(selector),
        config=json.dumps(conf),
        hostcomponentmap=json.dumps(hc),
        start_date=timezone.now(),
        finish_date=timezone.now(),
        status=config.Job.CREATED,
    )
    task.save()
    set_task_status(task, config.Job.CREATED)
    return task


def create_job(action, sub_action, selector, task_id=0):
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
    set_job_status(job.id, config.Job.CREATED)
    return job


def set_job_status(job_id, status, pid=0):
    JobLog.objects.filter(id=job_id).update(status=status, pid=pid, finish_date=timezone.now())
    status_api.set_job_status(job_id, status)


def set_task_status(task, status):
    task.status = status
    task.finish_date = timezone.now()
    task.save()
    status_api.set_task_status(task.id, status)


def get_task_obj(context, obj_id):
    if context == 'service':
        obj = ClusterObject.objects.get(id=obj_id)
    elif context == 'host':
        obj = Host.objects.get(id=obj_id)
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
    with transaction.atomic():
        if state is not None:
            set_action_state(action, task, obj, state)
        unlock_objects(obj)
        restore_hc(task, action, status)
        set_task_status(task, status)


def cook_log_name(job_id, tag, level, ext='txt'):
    return '{}-{}-{}.{}'.format(job_id, tag, level, ext)


def read_log(job_id, tag, level, log_type):
    fname = f'{config.LOG_DIR}/{job_id}-{tag}-{level}.{log_type}'
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


def log_check(job_id, title, res, msg):
    try:
        job = JobLog.objects.get(id=job_id)
        if job.status != config.Job.RUNNING:
            err('JOB_NOT_FOUND', f'job #{job.id} has status "{job.status}", not "running"')
    except JobLog.DoesNotExist:
        err('JOB_NOT_FOUND', f'no job with id #{job_id}')

    log_name = os.path.join(config.LOG_DIR, cook_log_name(job_id, 'check', 'out', 'json'))
    if os.path.exists(log_name):
        f = open(log_name, 'r+')
        raw = f.read()
        data = json.loads(raw)
        f.seek(0)
    else:
        f = open(log_name, 'w+')
        data = []
    data.append({'title': title, 'message': msg, 'result': res})
    f.write(json.dumps(data, indent=3))
    f.close()
    return data


def check_all_status():
    err('NOT_IMPLEMENTED')


def run_task(task, args=''):
    err_file = open(os.path.join(config.LOG_DIR, 'task_runner.err'), 'a+')
    proc = subprocess.Popen([
        os.path.join(config.BASE_DIR, 'task_runner.py'),
        str(task.id),
        args
    ], stderr=err_file)
    log.info("run task #%s, python process %s", task.id, proc.pid)
    task.pid = proc.pid
    task.save()
