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
module: adcm_cluster_info
short_description: report another cluster managed by this ADCM
description:
    - The C(adcm_cluster_info) plugin resolves a cluster managed by this ADCM by its C(uuid)
      or C(name) and reports its hosts, host-component map and services, so a bundle that
      integrates with another cluster can read its live topology instead of requiring it
      to be published somewhere and go stale.
    - Read-only. A cluster that is not found is reported with C(found=false) rather than
      failed, because whether this ADCM manages the cluster may be exactly the question.
options:
    uuid:
        description: ADCM uuid of the cluster (the C(cluster.uuid) runtime variable of its own jobs).
                     Preferred over I(name) when both are given.
        required: false
    name:
        description: Name of the cluster, used when I(uuid) is empty or not given.
        required: false
"""

EXAMPLES = r"""
- name: Resolve the ADB cluster
  adcm_cluster_info:
    uuid: "{{ record.adcm_cluster_uuid | default('') }}"
    name: "{{ record.name }}"
  register: adb_cluster
"""

RETURN = r"""
found:
    description: whether the cluster is managed by this ADCM.
    type: bool
cluster:
    description: id, name, uuid and state of the resolved cluster; empty when not found.
    type: dict
hosts:
    description: fqdns of every host of the resolved cluster.
    type: list
mapping:
    description: host fqdns keyed by '<service>.<component>'.
    type: dict
services:
    description: prototype names of the services of the resolved cluster.
    type: list
"""

import sys

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.executors.cluster_info import ADCMClusterInfoPluginExecutor


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMClusterInfoPluginExecutor
