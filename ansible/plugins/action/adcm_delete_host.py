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
module: adcm_delete_host
short_description: delete host from ADCM DB
description:
    - The C(adcm_delete_host) module is intended to delete host from ADCM DB.
      This module should be run in host context. Host Id is taken from context.
options:
'''

EXAMPLES = r'''
 - name: delete current host
   adcm_delete_host:
'''

RETURN = r'''
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
    _VALID_ARGS = frozenset(())

    def run(self, tmp=None, task_vars=None):
        def err(msg):
            return {"failed": True, "msg": msg}

        if not task_vars or 'context' not in task_vars:
            return err("There is no сontext in task vars")

        if task_vars['context']['type'] != 'host':
            return err('you can delete host only in host context')
        host_id = task_vars['context']['host_id']

        log.info('ansible module adcm_delete_host: host #%s', host_id)

        try:
            cm.api.delete_host_by_id(host_id)
        except AdcmEx as e:
            return err(e.code + ":" + e.msg)

        return {"failed": False, "changed": True}
