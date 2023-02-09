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
module: adcm_add_host_to_cluster
short_description: add host to cluster
description:
    - The C(adcm_add_host_to_cluster) module is intended to add existing host to cluster
      in ADCM DB. This module should be run in cluster or service context.
options:
  fqdn:
    description:
      - Fully qualified domain name of added host
    required: yes
  host_id:
    description:
      - Host ID of added host
    required: yes
"""

EXAMPLES = r"""
 - name: add existing host to cluster
   adcm_add_host_to_cluster:
     fqdn: my.host.org
"""

RETURN = r"""
result:
"""

import sys

from ansible.errors import AnsibleError

from ansible.plugins.action import ActionBase

sys.path.append("/adcm/python")
import adcm.init_django  # pylint: disable=unused-import
import cm.api
from cm.ansible_plugin import get_object_id_from_context
from cm.errors import AdcmEx
from cm.logger import logger


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(("fqdn", "host_id"))

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)
        msg = "You can add host only in cluster or service context"
        cluster_id = get_object_id_from_context(task_vars, "cluster_id", "cluster", "service", err_msg=msg)
        fqdn = self._task.args.get("fqdn", None)
        host_id = self._task.args.get("host_id", None)

        logger.info("ansible module: cluster_id %s, fqdn %s, host_id: %s", cluster_id, fqdn, host_id)
        try:
            cm.api.add_host_to_cluster_by_pk(cluster_id, fqdn, host_id)
        except AdcmEx as e:
            raise AnsibleError(e.code + ": " + e.msg) from e

        return {"failed": False, "changed": True}
