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

# pylint: disable=wrong-import-position, import-error

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1', 'supported_by': 'Arenadata'}

DOCUMENTATION = r'''
---
module: adcm_add_host
short_description: add host to ADCM DB
description:
    - The C(adcm_add_host) module is intended to add host to ADCM DB.
      This module should be run in host provider context.
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

from ansible.errors import AnsibleError

from ansible.plugins.action import ActionBase

sys.path.append('/adcm/python')
import adcm.init_django  # pylint: disable=unused-import
import cm.api
from cm.ansible_plugin import get_object_id_from_context
from cm.errors import AdcmEx
from cm.logger import logger


class ActionModule(ActionBase):

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(('fqdn', 'description'))

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)
        msg = 'You can add host only in host provider context'
        provider_id = get_object_id_from_context(task_vars, 'provider_id', 'provider', err_msg=msg)

        if 'fqdn' not in self._task.args:
            raise AnsibleError("fqdn is mandatory args of adcm_add_host")
        fqdn = self._task.args['fqdn']
        desc = ''
        if 'description' in self._task.args:
            desc = self._task.args['description']

        logger.info('ansible module adcm_add_host: provider %s, fqdn %s', provider_id, fqdn)

        try:
            host = cm.api.add_provider_host(provider_id, fqdn, desc)
        except AdcmEx as e:
            raise AnsibleError(e.code + ":" + e.msg) from e

        return {"failed": False, "changed": True, "host_id": host.id}
