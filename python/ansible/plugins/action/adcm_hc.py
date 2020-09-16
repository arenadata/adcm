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

# pylint: disable=wrong-import-position, unused-import, import-error

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1', 'supported_by': 'Arenadata'}

DOCUMENTATION = r'''
---
module: adcm_hc
short_description: change host component map (hc) for cluster
description:
    - The C(adcm_hc) module is intended to change host component map.
      This module should be run in cluster or service context. Cluster Id is taken from context.
options:
'''

EXAMPLES = r'''
 - name: add standby and node components to h1.company.com host
   adcm_hc:
     operations:
       -
         action: "add"
         service: "hadoop"
         component: standby
         host: "h1.company.com"
       -
         action: "remove"
         service: "hadoop"
         component: node
         host: "h1.company.com"

'''

RETURN = r'''
'''

import sys
from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase

sys.path.append('/adcm/python')
import adcm.init_django
import cm.api
from cm.ansible_plugin import get_context_id
from cm.errors import AdcmEx
from cm.logger import log


class ActionModule(ActionBase):

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(('operations',))
    _VALID_SUB_ARGS = frozenset(('action', 'service', 'component', 'host'))

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)
        msg = 'You can modify hc only in cluster or service context'
        cluster_id = get_context_id(task_vars, 'cluster', 'cluster_id', msg)
        job_id = task_vars['job']['id']
        ops = self._task.args['operations']

        log.info('ansible module adcm_hc: cluster #%s, ops: %s', cluster_id, ops)

        if not isinstance(ops, list):
            raise AnsibleError('Operations should be an array: %s' % ops)

        for op in ops:
            if not isinstance(op, dict):
                raise AnsibleError('Operation items should be a dictionary: %s' % op)
            args = frozenset(op.keys())
            if args.difference(self._VALID_SUB_ARGS):
                raise AnsibleError('Invalid operation arguments: %s' % op)

        try:
            cm.api.change_hc(job_id, cluster_id, ops)
        except AdcmEx as e:
            raise AnsibleError(e.code + ": " + e.msg) from e

        return {"failed": False, "changed": True}
