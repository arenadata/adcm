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


ANSIBLE_METADATA = {"metadata_version": "1.1", "supported_by": "Arenadata"}

DOCUMENTATION = r"""
---
module: adcm_state
short_description: Change state of object
description:
  - This is special ADCM only module which is useful for setting state for various ADCM objects.
  - There is support of cluster, service, host and providers states
  - This one is allowed to be used in various execution contexts.
options:
  - option-name: type
    required: true
    choises:
      - cluster
      - service
      - component
      - provider
      - host
    description: type of object which should be changed

  - option-name: state
    required: true
    type: string
    description: value of state which should be set

  - option-name: service_name
    required: false
    type: string
    description: useful in cluster context only.
    In that context you are able to set the state value for a service belongs to the cluster.

  - option-name: component_name
    required: false
    type: string
    description: Name of the component

  - option-name: host_id
    required: false
    type: int
    description: ID of the host

notes:
  - If type is 'service' ('component') there is no needs to specify service_name (component_name)
"""

EXAMPLES = r"""
- adcm_state:
    type: "cluster"
    state: "statey"
  register: out
- adcm_state:
    type: "service"
    service_name: "First"
    state: "bimba!"
"""

RETURN = r"""
state:
  returned: success
  type: str
  example: "operational"
"""


from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.executors.state import ADCMStatePluginExecutor


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMStatePluginExecutor
