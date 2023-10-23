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
      - type: service
        service_name: hdfs
      - type: component
        service_name: service
        component_name: component
      - type: cluster 
"""

EXAMPLES = r"""
- adcm_change_flag:
  operation: up
  objects:
  - type: service
    service_name: hdfs
  - type: component
    service_name: service
    component_name: component
  - type: cluster 

- adcm_change_flag:
  operation: down
  objects:
      - type: provider
      - type: host
        name: host_name
"""
import sys
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError

sys.path.append("/adcm/python")
import adcm.init_django  # pylint: disable=unused-import

from cm.ansible_plugin import get_context_object, check_context_type
from cm.status_api import update_event, UpdateEventType
from cm.logger import logger
from cm.flag import update_object_flag, remove_flag
from cm.models import (
    ClusterObject,
    ServiceComponent,
    get_object_cluster,
    HostProvider,
    Host,
    ADCMEntity,
    ADCMEntityStatus,
)

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
                raise AnsibleError("'Objects' value should be list of objects")

            if not self._task.args["objects"]:
                raise AnsibleError("'Objects' value should not be empty")

            for item in self._task.args["objects"]:
                item_type = item.get("type")
                if not item_type:
                    raise AnsibleError(message="'type' argument is mandatory for all items in 'objects'")

                if item_type == "component" and ("service_name" not in item or "component_name" not in item):
                    raise AnsibleError(message="'service_name' and 'component_name' is mandatory for type 'component'")
                if item_type == "service" and "service_name" not in item:
                    raise AnsibleError(message="'service_name' is mandatory for type 'service'")

    def _process_objects(self, task_vars: dict, objects: list, context_obj: ADCMEntity) -> None:
        err_msg = "Type {} should be used in {} context only"
        cluster = get_object_cluster(obj=context_obj)

        for item in self._task.args["objects"]:
            obj = None
            item_type = item.get("type")

            if item_type == "component":
                check_context_type(
                    task_vars=task_vars,
                    context_types=cluster_context_type,
                    err_msg=err_msg.format(item_type, cluster_context_type),
                )

                obj = ServiceComponent.objects.filter(
                    cluster=cluster,
                    prototype__name=item["component_name"],
                    service__prototype__name=item["service_name"],
                ).first()
            elif item_type == "service":
                check_context_type(
                    task_vars=task_vars,
                    context_types=cluster_context_type,
                    err_msg=err_msg.format(item_type, cluster_context_type),
                )

                obj = ClusterObject.objects.filter(cluster=cluster, prototype__name=item["service_name"]).first()
            elif item_type == "cluster":
                check_context_type(
                    task_vars=task_vars,
                    context_types=cluster_context_type,
                    err_msg=err_msg.format(item_type, cluster_context_type),
                )

                obj = cluster
            elif item_type == "provider":
                check_context_type(
                    task_vars=task_vars,
                    context_types=("provider", "host"),
                    err_msg=err_msg.format(item_type, ("provider", "host")),
                )

                if isinstance(context_obj, HostProvider):
                    obj = context_obj
                elif isinstance(context_obj, Host):
                    obj = context_obj.provider

            elif item_type == "host":
                check_context_type(
                    task_vars=task_vars,
                    context_types=("host",),
                    err_msg=err_msg.format(item_type, "host"),
                )

                obj = context_obj

            if not obj:
                logger.error("Object %s not found", item)
                continue

            objects.append(obj)

    def run(self, tmp=None, task_vars=None):
        super().run(tmp, task_vars)
        self._check_args()

        msg = ""
        if "msg" in self._task.args:
            msg = str(self._task.args["msg"])

        objects = []
        context_obj = get_context_object(task_vars=task_vars)
        if "objects" in self._task.args:
            self._process_objects(objects=objects, context_obj=context_obj, task_vars=task_vars)
        else:
            objects.append(context_obj)

        for obj in objects:
            if self._task.args["operation"] == "up":
                update_object_flag(obj=obj, msg=msg)
                update_event(object_=obj, update=(UpdateEventType.STATUS, ADCMEntityStatus.UP))
            elif self._task.args["operation"] == "down":
                remove_flag(obj=obj, msg=msg)
                update_event(object_=obj, update=(UpdateEventType.STATUS, ADCMEntityStatus.DOWN))

        return {"failed": False, "changed": True}
