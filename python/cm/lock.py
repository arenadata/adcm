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

# pylint: disable=too-many-branches,

from django.utils import timezone

import cm.config as config
from cm import api
from cm.adcm_config import obj_ref
from cm.logger import log
from cm.models import (
    ServiceComponent,
    Host,
    ClusterObject,
    ADCM,
    Cluster,
    HostProvider,
    TaskLog,
    JobLog,
)


def set_task_status(task, status, event):
    task.status = status
    task.finish_date = timezone.now()
    task.save()
    event.set_task_status(task.id, status)


def set_job_status(job_id, status, event, pid=0):
    JobLog.objects.filter(id=job_id).update(status=status, pid=pid, finish_date=timezone.now())
    event.set_job_status(job_id, status)


def lock_obj(obj, event):
    stack = obj.stack

    if not stack:
        stack = [obj.state]
    elif stack[-1] != obj.state:
        stack.append(obj.state)

    log.debug('lock %s, stack: %s', obj_ref(obj), stack)
    obj.stack = stack
    api.set_object_state(obj, config.Job.LOCKED, event)


def unlock_obj(obj, event):
    if obj.stack:
        stack = obj.stack
    else:
        log.warning('no stack in %s for unlock', obj_ref(obj))
        return
    try:
        state = stack.pop()
    except IndexError:
        log.warning('empty stack in %s for unlock', obj_ref(obj))
        return
    log.debug('unlock %s, stack: %s', obj_ref(obj), stack)
    obj.stack = stack
    api.set_object_state(obj, state, event)


def lock_objects(obj, event):
    if isinstance(obj, ServiceComponent):
        lock_obj(obj, event)
        lock_obj(obj.service, event)
        lock_obj(obj.cluster, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            lock_obj(host, event)
    elif isinstance(obj, ClusterObject):
        lock_obj(obj, event)
        lock_obj(obj.cluster, event)
        for sc in ServiceComponent.objects.filter(service=obj):
            lock_obj(sc, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            lock_obj(host, event)
    elif isinstance(obj, Host):
        lock_obj(obj, event)
        if obj.cluster:
            lock_obj(obj.cluster, event)
            for service in ClusterObject.objects.filter(cluster=obj.cluster):
                lock_obj(service, event)
            for sc in ServiceComponent.objects.filter(cluster=obj.cluster):
                lock_obj(sc, event)
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
        for sc in ServiceComponent.objects.filter(cluster=obj):
            lock_obj(sc, event)
        for host in Host.objects.filter(cluster=obj):
            lock_obj(host, event)
    else:
        log.warning('lock_objects: unknown object type: %s', obj)


def unlock_deleted_objects(job, event):
    if not job:
        log.warning('unlock_deleted_objects: no job')
        return
    selector = job.selector
    if 'cluster' in selector:
        cluster = Cluster.objects.get(id=selector['cluster'])
        unlock_objects(cluster, event)


def unlock_objects(obj, event, job=None):
    if isinstance(obj, ServiceComponent):
        unlock_obj(obj, event)
        unlock_obj(obj.service, event)
        unlock_obj(obj.cluster, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            unlock_obj(host, event)
    elif isinstance(obj, ClusterObject):
        unlock_obj(obj, event)
        unlock_obj(obj.cluster, event)
        for sc in ServiceComponent.objects.filter(service=obj):
            unlock_obj(sc, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            unlock_obj(host, event)
    elif isinstance(obj, Host):
        unlock_obj(obj, event)
        if obj.cluster:
            unlock_obj(obj.cluster, event)
            for service in ClusterObject.objects.filter(cluster=obj.cluster):
                unlock_obj(service, event)
            for sc in ServiceComponent.objects.filter(cluster=obj.cluster):
                unlock_obj(sc, event)
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
        for sc in ServiceComponent.objects.filter(cluster=obj):
            unlock_obj(sc, event)
        for host in Host.objects.filter(cluster=obj):
            unlock_obj(host, event)
    elif obj is None:
        unlock_deleted_objects(job, event)
    else:
        log.warning('unlock_objects: unknown object type: %s', obj)


def unlock_all(event):
    for obj in Cluster.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj, event)
    for obj in HostProvider.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj, event)
    for obj in ClusterObject.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj, event)
    for obj in ServiceComponent.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj, event)
    for obj in Host.objects.filter(state=config.Job.LOCKED):
        unlock_objects(obj, event)
    for task in TaskLog.objects.filter(status=config.Job.RUNNING):
        set_task_status(task, config.Job.ABORTED, event)
    for job in JobLog.objects.filter(status=config.Job.RUNNING):
        set_job_status(job.id, config.Job.ABORTED, event)
