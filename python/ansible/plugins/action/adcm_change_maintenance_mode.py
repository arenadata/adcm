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
---
module: adcm_change_maintenance_mode
short_description: Change Host, Service or Component maintenance mode to ON or OFF
description:
    - The C(adcm_change_maintenance_mode) module is intended to
      change Host, Service or Component maintenance mode to ON or OFF.
options:
  type:
    description: Entity type.
    required: true
    choices:
      - host
      - service
      - component
  value:
    description: Maintenance mode value True or False.
    required: True
    type: bool
"""

EXAMPLES = r"""
- name: Change host maintenance mode to True
  adcm_change_maintenance_mode:
    type: host
    value: True

- name: Change service maintenance mode to False
  adcm_change_maintenance_mode:
    type: service
    value: False
"""

import sys

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible_plugin.maintenance_mode import get_object, validate_args, validate_obj
from cm.models import MaintenanceMode
from cm.services.maintenance_mode import set_maintenance_mode


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(["type", "value"])

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)

        error = validate_args(task_args=self._task.args)
        if error is not None:
            raise error

        obj, error = get_object(task_vars=task_vars, obj_type=self._task.args["type"])
        if error is not None:
            raise error

        error = validate_obj(obj=obj)
        if error is not None:
            raise error

        value = MaintenanceMode.ON if self._task.args["value"] else MaintenanceMode.OFF
        try:
            set_maintenance_mode(obj=obj, value=value)
        except Exception as e:  # noqa: BLE001
            raise AnsibleActionFail("Unexpected error occurred while changing object's maintenance mode") from e

        return {"failed": False, "changed": True}
