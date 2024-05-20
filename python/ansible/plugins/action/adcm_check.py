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
module: adcm_check
short_description: add entity to log storage in json format
description:
    - The C(adcm_check) module is intended to log result of some checks to structured JSON log
      storage. This log can be seen via ADCM user interface. Each invoke of C(adcm_check) add one
      entry to json log storage linked with ADCM job. You can invoke C(adcm_check) with one job id
      any number of time per playbook.
options:
  group_title:
    description:
      - Name of group check
    required: no
  group_success_msg:
    description:
      - Description of success check or success results of check for group
    required: no
  group_fail_msg:
    description:
      - Description of fail check or fail results of check for group
    required: no
  title:
    description:
      - Name of check
    required: yes
  result:
    description:
      - Result of check, yes/no
    required: yes
    type: bool
  msg:
    description:
      - Description of check or results of check
    required:
      - yes, if no 'success_msg' and 'fail_msg' fields
  success_msg:
    description:
      - Description of success check or success results of check
    required:
      - yes, if no 'msg' field
  fail_msg:
    description:
      - Description of fail check or fail results of check
    required:
      - yes, if no 'msg' field
"""

EXAMPLES = r"""
- name: ADCM Check
  adcm_check:
    title: "Check"
    msg: "This is message"
    result: yes

- name: ADCM Check
  adcm_check:
    title: "Check"
    success_msg: "This is success message"
    fail_msg: "This is fail message"
    result: yes

- name: ADCM Check
  adcm_check:
    group_title: "Group 1"
    group_success_msg: "This is success message"
    group_fail_msg: "This is fail message"
    title: "Check"
    msg: "This is message"
    result: yes
"""

RETURN = r"""
result:
  check: JSON log of all checks for this ADCM job
"""

import sys

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.executors.check import ADCMCheckPluginExecutor


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMCheckPluginExecutor
