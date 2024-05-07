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


ANSIBLE_METADATA = {"metadata_version": "1.1", "supported_by": "Arenadata"}

DOCUMENTATION = r"""
---
module: adcm_remove_host_from_cluster
short_description: remove host from cluster
description:
    - The C(adcm_add_host_to_cluster) module is intended to remove host from cluster
      in ADCM DB. This module should be run in cluster or service context.
options:
  fqdn:
    description:
      - Fully qualified domain name of added host
    required: yes/no
  host_id:
    description:
      - Host ID of added host
    required: yes/no
"""

EXAMPLES = r"""
 - name: remove host from cluster
   adcm_remove_host_from_cluster:
     fqdn: my.host.org
"""

RETURN = ""

import sys

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.executors.remove_host_from_cluster import ADCMRemoveHostFromClusterPluginExecutor


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMRemoveHostFromClusterPluginExecutor
