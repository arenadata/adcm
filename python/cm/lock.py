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

from cm import config
from cm.adcm_config import obj_ref
from cm.hierarchy import Tree
from cm.logger import log
from cm.models import (
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
    obj.set_state(config.Job.LOCKED, event)


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
    obj.set_state(state, event)


def lock_objects(obj, event):
    tree = Tree(obj)
    for node in tree.get_all_affected(tree.built_from):
        _lock_obj(node.value, event)


def unlock_objects(obj, event):
    tree = Tree(obj)
    for node in tree.get_all_affected(tree.built_from):
        _unlock_obj(node.value, event)


def unlock_all(event):
    for obj in Cluster.objects.filter(state=config.Job.LOCKED):
        _unlock_obj(obj, event)
    for obj in HostProvider.objects.filter(state=config.Job.LOCKED):
        _unlock_obj(obj, event)
    for obj in ClusterObject.objects.filter(state=config.Job.LOCKED):
        _unlock_obj(obj, event)
    for obj in ServiceComponent.objects.filter(state=config.Job.LOCKED):
        _unlock_obj(obj, event)
    for obj in Host.objects.filter(state=config.Job.LOCKED):
        _unlock_obj(obj, event)
