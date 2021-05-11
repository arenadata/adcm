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

import cm.config as config
from cm import api
from cm.adcm_config import obj_ref
from cm.logger import log
from cm.models import (
    ADCM,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    ServiceComponent,
)


def _lock_obj(obj, event):
    stack = obj.stack

    if not stack:
        stack = [obj.state]
    elif stack[-1] != obj.state:
        stack.append(obj.state)

    log.debug('lock %s, stack: %s', obj_ref(obj), stack)
    obj.stack = stack
    api.set_object_state(obj, config.Job.LOCKED, event)


def _unlock_obj(obj, event):
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
    log.debug('unlock %s, stack: %s, state: %s', obj_ref(obj), stack, state)
    obj.stack = stack
    api.set_object_state(obj, state, event)


def lock_objects(obj, event):
    if isinstance(obj, ServiceComponent):
        _lock_obj(obj, event)
        _lock_obj(obj.service, event)
        _lock_obj(obj.cluster, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            _lock_obj(host, event)
    elif isinstance(obj, ClusterObject):
        _lock_obj(obj, event)
        _lock_obj(obj.cluster, event)
        for sc in ServiceComponent.objects.filter(service=obj):
            _lock_obj(sc, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            _lock_obj(host, event)
    elif isinstance(obj, Host):
        _lock_obj(obj, event)
        if obj.cluster:
            _lock_obj(obj.cluster, event)
            for service in ClusterObject.objects.filter(cluster=obj.cluster):
                _lock_obj(service, event)
            for sc in ServiceComponent.objects.filter(cluster=obj.cluster):
                _lock_obj(sc, event)
    elif isinstance(obj, HostProvider):
        _lock_obj(obj, event)
        for host in Host.objects.filter(provider=obj):
            _lock_obj(host, event)
    elif isinstance(obj, ADCM):
        _lock_obj(obj, event)
    elif isinstance(obj, Cluster):
        _lock_obj(obj, event)
        for service in ClusterObject.objects.filter(cluster=obj):
            _lock_obj(service, event)
        for sc in ServiceComponent.objects.filter(cluster=obj):
            _lock_obj(sc, event)
        for host in Host.objects.filter(cluster=obj):
            _lock_obj(host, event)
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
        _unlock_obj(obj, event)
        _unlock_obj(obj.service, event)
        _unlock_obj(obj.cluster, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            _unlock_obj(host, event)
    elif isinstance(obj, ClusterObject):
        _unlock_obj(obj, event)
        _unlock_obj(obj.cluster, event)
        for sc in ServiceComponent.objects.filter(service=obj):
            _unlock_obj(sc, event)
        for host in Host.objects.filter(cluster=obj.cluster):
            _unlock_obj(host, event)
    elif isinstance(obj, Host):
        _unlock_obj(obj, event)
        if obj.cluster:
            _unlock_obj(obj.cluster, event)
            for service in ClusterObject.objects.filter(cluster=obj.cluster):
                _unlock_obj(service, event)
            for sc in ServiceComponent.objects.filter(cluster=obj.cluster):
                _unlock_obj(sc, event)
    elif isinstance(obj, HostProvider):
        _unlock_obj(obj, event)
        for host in Host.objects.filter(provider=obj):
            _unlock_obj(host, event)
    elif isinstance(obj, ADCM):
        _unlock_obj(obj, event)
    elif isinstance(obj, Cluster):
        _unlock_obj(obj, event)
        for service in ClusterObject.objects.filter(cluster=obj):
            _unlock_obj(service, event)
        for sc in ServiceComponent.objects.filter(cluster=obj):
            _unlock_obj(sc, event)
        for host in Host.objects.filter(cluster=obj):
            _unlock_obj(host, event)
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
