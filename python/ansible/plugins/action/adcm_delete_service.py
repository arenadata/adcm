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
module: adcm_delete_service
short_description: delete service from cluster in ADCM DB
description:
    - The C(adcm_delete_service) module is intended to delete service from ADCM DB.
      This module should be run in service context. Service Id is taken from context.
options:
'''

EXAMPLES = r'''
 - name: delete service from cluster
   adcm_delete_service:
'''

RETURN = r'''
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
    _VALID_ARGS = frozenset(())

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)
        service = self._task.args.get('service', None)
        if service:
            msg = 'You can delete service by name only in cluster context'
            cluster_id = get_object_id_from_context(task_vars, 'cluster_id', 'cluster', err_msg=msg)
            logger.info('ansible module adcm_delete_service: service "%s"', service)
            try:
                cm.api.delete_service_by_name(service, cluster_id)
            except AdcmEx as e:
                raise AnsibleError(e.code + ":" + e.msg) from e
        else:
            msg = 'You can delete service only in service context'
            service_id = get_object_id_from_context(task_vars, 'service_id', 'service', err_msg=msg)
            logger.info('ansible module adcm_delete_service: service #%s', service_id)
            try:
                cm.api.delete_service_by_pk(service_id)
            except AdcmEx as e:
                raise AnsibleError(e.code + ":" + e.msg) from e

        return {"failed": False, "changed": True}
