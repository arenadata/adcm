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


DOCUMENTATION = """
module: adcm_change_flag
short_description: Raise or Lower flags on Cluster, Service, Component, Provider or Host
description:
    - The C(adcm_change_flag) module is intended to raise or lower on Cluster, Service, Component, Provider or Host.
options:
  operation:
    description: Operation over flag.
    required: True
    choices:
      - up
      - down
  name:
    description: |
      Internal flag name. Used for managing flags, including embedded ones.
      If not specified in case of "down" operation all object's flags will be lowered.
    required: False
    type: string
  msg:
    description: |
      Additional flag message, to use in pattern "<object> has a flag: <msg>".
      It might be used if you want several different flags on the same object.
      In case of embedded flags management will overwrite the default message.
    required: False
    type: string
  objects:
    description: |
      List of Services or Components on which you need to raise/lower the flag.
      If this parameter is not specified, flag on action context object will be raised or lowered.
      If you want to raise or lower flag on cluster you can add `- type: cluster` entry.
    required: False
    type: list
    elements: dict
    sample:
      - type: cluster
"""

EXAMPLES = """
# raise / up

- adcm_change_flag:
    operation: up
    name: my_custom_flag
    objects:
      - type: component
        service_name: kafka
        component_name: kafka_broker

- adcm_change_flag:
    operation: up
    name: adcm_outdated_config
    objects:
      - type: component
        service_name: kafka
        component_name: kafka_broker

# lower / down

- adcm_change_flag:
    name: my_custom_flag
    operation: down

- adcm_change_flag:
    operation: down
    objects:
      - type: service
"""

import sys

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip
from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.executors.change_flag import ADCMChangeFlagPluginExecutor


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMChangeFlagPluginExecutor
