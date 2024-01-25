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


ANSIBLE_METADATA = {"metadata_version": "1.0", "supported_by": "Arenadata"}

DOCUMENTATION = r"""
short_description: add entry to log storage
description:
    - The C(adcm_custom_log) module is intended to log result of some checks to structured JSON or
      TXT in log storage. This log can be seen via ADCM user interface. Each invoke of
      C(adcm_custom_log) add one entry to json or txt log linked with ADCM job. You can invoke
      C(adcm_custom_log) with one job id any number of time per playbook.
options:
  name:
    description:
     - Name of log
    required: yes
  format:
    description:
     - Format of body, json/txt
    required: yes
  path:
    description:
     - Path of file on localhost with text for log
    required: yes, if field 'content' is none
  content:
    description:
     - Text for log
    required: yes, if field 'path' is none
"""

EXAMPLES = r"""
 - name: custom log
   adcm_custom_log:
     name: custom
     format: json
     path: /adcm/data/log/custom.txt

 - name: custom log
   adcm_custom_log:
     name: custom
     format: txt
     content: It is text
"""

RETURN = r"""
"""

from binascii import Error
import sys
import base64

from ansible.plugins.action import ActionBase

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from cm.ansible_plugin import create_custom_log
from cm.errors import AdcmEx
from cm.logger import logger


class ActionModule(ActionBase):
    _VALID_ARGS = frozenset(("name", "format", "path", "content"))

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)
        if task_vars is not None and "job" in task_vars or "id" in task_vars["job"]:
            job_id = task_vars["job"]["id"]

        name = self._task.args.get("name")
        log_format = self._task.args.get("format")
        path = self._task.args.get("path")
        content = self._task.args.get("content")
        if not name and log_format and (path or content):
            return {
                "failed": True,
                "msg": "name, format and path or content are mandatory args of adcm_custom_log",
            }

        try:
            if path is None:
                logger.debug("ansible adcm_custom_log: %s, %s, %s, %s", job_id, name, log_format, content)
                create_custom_log(job_id=job_id, name=name, log_format=log_format, body=content)
            else:
                logger.debug("ansible adcm_custom_log: %s, %s, %s, %s", job_id, name, log_format, path)
                slurp_return = self._execute_module(
                    module_name="slurp", module_args={"src": path}, task_vars=task_vars, tmp=tmp
                )
                if "failed" in slurp_return and slurp_return["failed"]:
                    raise AdcmEx("UNKNOWN_ERROR", msg=slurp_return["msg"])

                try:
                    body = base64.standard_b64decode(slurp_return["content"]).decode()
                except Error as error:
                    raise AdcmEx("UNKNOWN_ERROR", msg="Error b64decode for slurp module") from error
                except UnicodeDecodeError as error:
                    raise AdcmEx("UNKNOWN_ERROR", msg="Error UnicodeDecodeError for slurp module") from error

                create_custom_log(job_id=job_id, name=name, log_format=log_format, body=body)

        except AdcmEx as e:
            return {"failed": True, "msg": f"{e.code}: {e.msg}"}

        return {"failed": False, "changed": False}
