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

RETURN = ""

from binascii import Error
from pathlib import Path
from typing import Any
import sys
import base64

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip


from ansible_plugin.base import ADCMAnsiblePlugin
from ansible_plugin.errors import PluginRuntimeError
from ansible_plugin.executors.custom_log import ADCMCustomLogPluginExecutor


class ActionModule(ADCMAnsiblePlugin):
    executor_class = ADCMCustomLogPluginExecutor

    def _get_executor(self, tmp: Any, task_vars: Any) -> ADCMCustomLogPluginExecutor:
        def retrieve_from_path_impl(_, path: Path) -> str:
            slurp_return = self._execute_module(
                module_name="slurp", module_args={"src": str(path)}, task_vars=task_vars, tmp=tmp
            )
            if slurp_return.get("failed"):
                raise PluginRuntimeError(message=slurp_return["msg"])

            try:
                return base64.standard_b64decode(slurp_return["content"]).decode()
            except Error as error:
                raise PluginRuntimeError(message="Error `b64decode` for slurp module") from error
            except UnicodeDecodeError as error:
                raise PluginRuntimeError(message="Error `UnicodeDecodeError` for slurp module") from error

        return self.executor_class[retrieve_from_path_impl](arguments=self._task.args, runtime_vars=task_vars)
