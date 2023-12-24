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

import adcm.init_django  # pylint: disable=unused-import
from cm.ansible_plugin import get_object_id_from_context
from cm.api import load_mm_objects
from cm.status_api import send_object_update_event
from cm.issue import update_hierarchy_issues
from cm.models import ClusterObject, Host, ServiceComponent


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(["type", "value"])

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)

        type_class_map = {
            "host": Host,
            "service": ClusterObject,
            "component": ServiceComponent,
        }
        type_choices = set(type_class_map.keys())

        if not self._task.args.get("type"):
            raise AnsibleActionFail('"type" option is required')

        if self._task.args.get("value") is None:
            raise AnsibleActionFail('"value" option is required')

        if self._task.args["type"] not in type_choices:
            raise AnsibleActionFail(f'"type" should be one of {type_choices}')

        if not isinstance(self._task.args["value"], bool):
            raise AnsibleActionFail('"value" should be boolean')

        obj_type = self._task.args["type"]
        context_type = obj_type
        if obj_type == "host":
            context_type = "cluster"

        obj_value = "on" if self._task.args["value"] else "off"
        obj_pk = get_object_id_from_context(
            task_vars=task_vars,
            id_type=f"{obj_type}_id",
            context_types=(context_type,),
            err_msg=f'You can change "{obj_type}" maintenance mode only in {context_type} context',
        )

        obj = type_class_map[obj_type].objects.filter(pk=obj_pk).first()
        if not obj:
            raise AnsibleActionFail(f'Object of type "{obj_type}" with PK "{obj_pk}" does not exist')

        if obj.maintenance_mode != "changing":
            raise AnsibleActionFail('Only "changing" state of object maintenance mode can be changed')

        obj.maintenance_mode = obj_value
        obj.save()
        send_object_update_event(object_=obj, changes={"maintenanceMode": obj.maintenance_mode})
        update_hierarchy_issues(obj.cluster)
        load_mm_objects()

        return {"failed": False, "changed": True}
