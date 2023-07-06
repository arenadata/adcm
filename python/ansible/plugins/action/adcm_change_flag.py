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
module: adcm_change_flag
short_description: Raise or Lower flags on  Host, Service, Component or Cluster
description:
    - The C(adcm_change_flag) module is intended to raise or lower on Host, Service, Component.
options:
  operation:
    description: Operation over flag.
    required: True
    choices:
      - up
      - down
  msg:
    description: Additional flag message, to use in pattern "<object> has an outdated configuration: <msg>". It might be used if you want several different flags in the same objects. In case of down operation, if message specified then down only flag with specified message. 
    required: False
    type: string
  objects:
    description: List of Services or Components on which you need to raise/lower the flag. If this parameter not specified raise or lower flag on action context object. If you want to raise or lower flag on cluster you needed action in cluster context.
    required: False
    type: list
    elements: dict
    sample:
      - component: datanode
      - service: yarn
"""

EXAMPLES = r"""
- adcm_change_flag:
  operation: up
  objects:
    - service: hdfs
    - service: yarn

- adcm_change_flag:
  operation: down
  objects:
    - component: datanode
    - service: yarn
"""
import sys
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError

sys.path.append("/adcm/python")
import adcm.init_django  # pylint: disable=unused-import


from cm.ansible_plugin import get_context_object, check_context_type
from cm.flag import update_flags, remove_flag
from cm.models import ClusterObject, ServiceComponent, get_object_cluster

cluster_context_type = ("cluster", "service", "component")


class ActionModule(ActionBase):
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(("operation", "msg", "objects"))

    def _check_args(self):
        if "operation" not in self._task.args:
            raise AnsibleError("'Operation' is mandatory args of adcm_change_flag")

        if self._task.args["operation"] not in ("up", "down"):
            raise AnsibleError(f"'Operation' value must be 'up' or 'down', not {self._task.args['operation']}")

        if "objects" in self._task.args:
            if not isinstance(self._task.args["objects"], list):
                raise AnsibleError("'Objects' value must be list of services and/or components")

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)
        self._check_args()

        msg = ""
        if "msg" in self._task.args:
            msg = str(self._task.args["msg"])

        objects = []
        context_obj = get_context_object(task_vars=task_vars)
        if "objects" in self._task.args:
            check_context_type(
                task_vars=task_vars,
                context_types=cluster_context_type,
                err_msg="'Objects' parameter must be used in 'cluster', 'service' or 'component' context only",
            )
            cluster = get_object_cluster(obj=context_obj)

            for item in self._task.args["objects"]:
                obj = None
                if "component" in item and "service" in item:
                    obj = ServiceComponent.objects.filter(
                        cluster=cluster, prototype__name=item["component"], service__prototype__name=item["service"]
                    ).first()
                elif "service" in item:
                    obj = ClusterObject.objects.filter(cluster=cluster, prototype__name=item["service"]).first()

                if not obj:
                    raise AnsibleError("'Objects' item must contain service and/or component name")

                objects.append(obj)
        else:
            objects.append(context_obj)

        for obj in objects:
            if self._task.args["operation"] == "up":
                update_flags(obj=obj, msg=msg)
            elif self._task.args["operation"] == "down":
                remove_flag(obj=obj, msg=msg)

        return {"failed": False, "changed": True}
