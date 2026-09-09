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


import sys

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.executors.config import ADCMConfigPluginExecutor

ANSIBLE_METADATA = {"metadata_version": "1.1", "supported_by": "Arenadata"}
DOCUMENTATION = r"""
---
module: adcm_config
short_description: Change values in config in runtime
description:
  - This is special ADCM only module which is useful for setting of specified config key
    or set of config keys for various ADCM objects.
  - There is support of cluster, service, component, host and providers config.
  - This one is allowed to be used in various execution contexts.
options:
  - option-name: type
    required: true
    choices:
      - cluster
      - service
      - component
      - host
      - provider
    description: type of object which should be changed

  - option-name: key
    required: false
    type: string
    description: name of key which should be set

  - option-name: value
    required: false
    description: value which should be set

  - option-name: parameters
    required: false
    type: list
    description: list of keys and values which should be set

  - option-name: service_name
    required: false
    type: string
    description: useful in cluster and component context.
    In that context you are able to set a config value for a service belongs to the cluster.

  - option-name: component_name
    required: false
    type: string
    description: useful in cluster, service and component context.
    In that context you are able to set a config value for a component belongs to the cluster.

notes:
  - If type is "service", there is no need to specify `service_name` if config of context's service should be changed.
    Same for "component" and `component_name`.
"""
EXAMPLES = r"""
- adcm_config:
    type: "service"
    service_name: "First"
    key: "some_int"
    value: *new_int
  register: out

- adcm_config:
    type: "cluster"
    key: "some_map"
    value:
      key1: value1
      key2: value2

- adcm_config:
    type: "host"
    parameters:
      - key: "some_group/some_string"
        value: "string"
      - key: "some_map"
        value:
          key1: value1
          key2: value2
      - key: "some_string"
        value: "string"
"""
RETURN = r"""
value:
  returned: success
  type: complex
"""


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMConfigPluginExecutor
