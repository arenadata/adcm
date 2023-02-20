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
# ruff: noqa: E402,F401

from __future__ import absolute_import, division, print_function

__metaclass__ = type  # pylint: disable=invalid-name

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

from ansible.plugins.action import ActionBase

sys.path.append("/adcm/python")
import adcm.init_django  # pylint: disable=unused-import
from cm.ansible_plugin import log_check
from cm.errors import AdcmEx
from cm.logger import logger


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(
        (
            "title",
            "result",
            "msg",
            "fail_msg",
            "success_msg",
            "group_title",
            "group_success_msg",
            "group_fail_msg",
        )
    )

    def run(self, tmp=None, task_vars=None):  # pylint: disable=too-many-locals
        super().run(tmp, task_vars)
        job_id = None
        if task_vars is not None and "job" in task_vars or "id" in task_vars["job"]:
            job_id = task_vars["job"]["id"]

        old_optional_condition = "msg" in self._task.args
        new_optional_condition = "fail_msg" in self._task.args and "success_msg" in self._task.args
        optional_condition = old_optional_condition or new_optional_condition
        required_condition = "title" in self._task.args and "result" in self._task.args and optional_condition

        if not required_condition:
            return {
                "failed": True,
                "msg": "title, result and msg, fail_msg or success" "_msg are mandatory args of adcm_check",
            }

        title = self._task.args["title"]
        result = self._task.args["result"]
        msg = self._task.args.get("msg", "")
        fail_msg = self._task.args.get("fail_msg", "")
        success_msg = self._task.args.get("success_msg", "")

        group_title = self._task.args.get("group_title", "")
        group_fail_msg = self._task.args.get("group_fail_msg", "")
        group_success_msg = self._task.args.get("group_success_msg", "")

        if result:
            msg = success_msg if success_msg else msg
        else:
            msg = fail_msg if fail_msg else msg

        group = {"title": group_title, "success_msg": group_success_msg, "fail_msg": group_fail_msg}

        check = {
            "title": title,
            "result": result,
            "message": msg,
        }

        logger.debug(
            "ansible adcm_check: %s, %s",
            ", ".join([f"{k}: {v}" for k, v in group.items() if v]),
            ", ".join([f"{k}: {v}" for k, v in check.items() if v]),
        )

        try:
            log_check(job_id, group, check)
        except AdcmEx as e:
            return {"failed": True, "msg": e.code + ":" + e.msg}

        return {"failed": False, "changed": False}
