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
module: adcm_delete_service
short_description: delete service from cluster in ADCM DB
description:
  - The C(adcm_delete_service) module is intended to delete service from ADCM DB.
    This module should be run in cluster or service context.
    Service ID is taken from context when name is not specified.
options:
  service:
    description:
      - Name of the service to delete
    required: no
"""

EXAMPLES = r"""
  - adcm_delete_service:
      service: delete service from cluster

  - adcm_delete_service:
"""

RETURN = ""

import sys

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.executors.delete_service import ADCMDeleteServicePluginExecutor


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMDeleteServicePluginExecutor
