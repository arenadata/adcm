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

from cm.errors import AdcmEx
from cm.logger import logger
from cm.models import Action, Prototype


def task_generator(action, selector):
    logger.debug("call task_generator: %s", action)
    try:
        service = Prototype.objects.get(bundle=action.prototype.bundle, type='service', name='ZOOKEEPER', version='1.2')
    except Prototype.DoesNotExist:
        raise AdcmEx('TASK_GENERATOR_ERROR', 'service ZOOKEEPER not found')

    try:
        stop = Action.objects.get(prototype=service, name='stop')
    except Prototype.DoesNotExist:
        raise AdcmEx('TASK_GENERATOR_ERROR', 'action stop of service ZOOKEEPER not found')

    try:
        start = Action.objects.get(prototype=service, name='start')
    except Prototype.DoesNotExist:
        raise AdcmEx('TASK_GENERATOR_ERROR', 'action start of service ZOOKEEPER not found')

    return (
        {'action': stop, 'selector': selector},
        {'action': start, 'selector': selector},
    )
