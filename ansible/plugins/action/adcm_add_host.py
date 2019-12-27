#!/usr/bin/python
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

# pylint: disable=wrong-import-position,unused-import

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1', 'supported_by': 'Arenadata'}

DOCUMENTATION = r'''
---
module: adcm_add_host
short_description: add host to ADCM DB
description:
    - The C(adcm_add_host) module is intended to add host to ADCM DB.
      Should be run in host provider context.
options:
  fqdn:
    description:
      - Fully qualified domain name of added host
    required: yes
  description:
    description:
      - Comment
    required: no
'''

EXAMPLES = r'''
 - name: add new host
   adcm_add_host:
     fqdn: my.host.org
     description: "add my host"
'''

RETURN = r'''
result:
  host_id: ID of new created host
'''

import sys
from ansible.plugins.action import ActionBase

sys.path.append('/adcm')
import adcm.init_django
import cm.api
from cm.errors import AdcmEx
from cm.logger import log


class ActionModule(ActionBase):

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(('fqdn', 'description'))

    def run(self, tmp=None, task_vars=None):
        def err(msg):
            return {"failed": True, "msg": msg}

        log.debug('QQ enter add_host')

        if not task_vars or 'context' not in task_vars:
            return err("There is no сontext in task vars")

        if task_vars['context']['type'] != 'provider':
            return err('you can add host only in provider context')
        provider_id = task_vars['context']['provider_id']

        if 'fqdn' not in self._task.args:
            return err("fqdn is mandatory args of adcm_add_host")

        desc = None
        fqdn = self._task.args['fqdn']
        if 'description' in self._task.args:
            desc = self._task.args['description']

        log.debug('ansible adcm_add_host: provider %s, fqdn %s', provider_id, fqdn)

        try:
            host = cm.api.add_provider_host(provider_id, fqdn, desc)
        except AdcmEx as e:
            return err(e.code + ":" + e.msg)

        return {"failed": False, "changed": True, "host_id": host.id}
