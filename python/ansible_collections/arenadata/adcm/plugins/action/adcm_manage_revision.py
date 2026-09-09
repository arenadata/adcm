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
module: adcm_manage_revision
short_description:
    Allows to collect information about changed object configuration parameters and make configuration revisions
description:
    - This is special ADCM only module which is sets revisions - marks the configuration of the service/component
      (hereinafter referred to as the object) as applied;
    - Gives a configuration diff for the object
      (the difference between the current applied configuration and the previous version)
    - There is support for all objects config.
    - This one is allowed to be used in various execution contexts.
options:
  operation:
    description: The operation to perform. get_primary_diff - Get the difference between the passed and previous
      configuration revision; set_primary_revision - Set a configuration revision as applied.
    required: True
    choices:
      - get_primary_diff
      - set_primary_revision
  objects:
    description: The list of objects to operate on (set configs revisions / get configs diff)
    type: list
    required: true
    elements: dict
    sample:
      - type: component
        service_name: "kafka"
        component_name: "broker"
"""

EXAMPLES = r"""
- name: Getting difference between current/previous
  adcm_manage_revision:
    operation: get_primary_diff
    objects:
      - type: component
        service_name: "kafka"
        component_name: "broker"
  register: diff_result

- name: Set configuration as applied
  adcm_manage_revision:
    operation: set_primary_revision
    objects:
      - type: component
        service_name: "kafka"
        component_name: "broker"
"""

RETURN = r"""
value:
  description: Differences between current and previous config with revision
  returned: when specified operation is `get_primary_diff`
  type: dict
  sample: {
    "CLUSTER": {
        "diff": {"param_name1": {"value": ["old1", "new1"]}, "param_name2": {"value": ["old2", "new2"]}},
        "attr_diff": {}
    },
    "components": {
        "service_name.component_name":{
            "diff": {},
            "attr_diff": {"activatable_group": {"active": {"value": [True, False]}}}
        }
    },
  }
"""


import sys

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.executors.manage_revision import ADCMManageRevisionPluginExecutor


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMManageRevisionPluginExecutor
