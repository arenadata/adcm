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
module: adcm_config_host_group_info
short_description: report configuration host groups of an object
description:
    - The C(adcm_config_host_group_info) plugin reports the configuration host groups of a
      cluster, service, component or provider, addressed the same way as in C(adcm_config) -
      by C(type) plus C(service_name)/C(component_name) where applicable.
    - Read-only counterpart of C(adcm_config_host_group). Returns every group of the object
      with its hosts; with C(name) it additionally reports whether that group exists and
      which fqdns it holds.
options:
    type:
        description: Type of the object owning the groups.
        required: true
        choices: [cluster, service, component, provider]
    service_name:
        description: Name of the service owning the groups (with C(type=service)) or of the
                     service of the component owning them (with C(type=component)).
        required: false
    component_name:
        description: Name of the component owning the groups (with C(type=component)).
        required: false
    name:
        description: Name of one group to report C(exists) and C(hosts) for.
        required: false
"""

EXAMPLES = r"""
- name: List the per-cluster configuration groups
  adcm_config_host_group_info:
    type: service
    service_name: adb_clusters
  register: attached_groups

- name: Read one configuration group
  adcm_config_host_group_info:
    type: service
    service_name: adb_clusters
    name: "{{ record.name }}"
  register: cluster_group
"""

RETURN = r"""
groups:
    description: id, name, description and hosts of every group of the object.
    type: list
names:
    description: just the group names.
    type: list
exists:
    description: whether the group I(name) exists (only when I(name) is given).
    type: bool
hosts:
    description: fqdns the group I(name) holds, empty when it doesn't exist
                 (only when I(name) is given).
    type: list
"""

import sys

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.executors.config_host_group_info import ADCMConfigHostGroupInfoPluginExecutor


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMConfigHostGroupInfoPluginExecutor
