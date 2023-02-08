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

# pylint: disable=wrong-import-order,wrong-import-position

from __future__ import absolute_import, division, print_function

__metaclass__ = type  # pylint: disable=invalid-name

ANSIBLE_METADATA = {"metadata_version": "1.1", "supported_by": "Arenadata"}

DOCUMENTATION = r"""
---
module: adcm_hc
short_description: change host component map (hc) for cluster
description:
    - The C(adcm_hc) module is intended to change host component map.
      This module should be run in cluster or service context. Cluster Id is taken from context.
options:
"""

EXAMPLES = r"""
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

"""

RETURN = r"""
"""

import sys

from ansible.errors import AnsibleError

from ansible.plugins.action import ActionBase

sys.path.append("/adcm/python")
import adcm.init_django  # pylint: disable=unused-import
from cm.ansible_plugin import change_hc, get_object_id_from_context
from cm.errors import AdcmEx
from cm.logger import logger


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(("operations",))
    _VALID_SUB_ARGS = frozenset(("action", "service", "component", "host"))

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)
        msg = "You can modify hc only in cluster, service or component context"
        cluster_id = get_object_id_from_context(task_vars, "cluster_id", "cluster", "service", "component", err_msg=msg)
        job_id = task_vars["job"]["id"]
        operations = self._task.args["operations"]

        logger.info("ansible module adcm_hc: cluster #%s, ops: %s", cluster_id, operations)

        if not isinstance(operations, list):
            raise AnsibleError(f"Operations should be an array: {operations}")

        for operation in operations:
            if not isinstance(operation, dict):
                raise AnsibleError(f"Operation items should be a dictionary: {operation}")
            args = frozenset(operation.keys())
            if args.difference(self._VALID_SUB_ARGS):
                raise AnsibleError(f"Invalid operation arguments: {operation}")

        try:
            change_hc(job_id, cluster_id, operations)
        except AdcmEx as e:
            raise AnsibleError(e.code + ": " + e.msg) from e

        return {"failed": False, "changed": True}
