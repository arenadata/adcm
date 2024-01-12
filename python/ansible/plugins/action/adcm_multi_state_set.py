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

from cm.ansible_plugin import (
    ContextActionModule,
    set_cluster_multi_state,
    set_component_multi_state,
    set_component_multi_state_by_name,
    set_host_multi_state,
    set_provider_multi_state,
    set_service_multi_state,
    set_service_multi_state_by_name,
)

ANSIBLE_METADATA = {"metadata_version": "1.1", "supported_by": "Arenadata"}

DOCUMENTATION = r"""
---
module: adcm_multi_state_set
short_description: Add one state to multi_state field
description:
  - This is special ADCM only module which is useful for changing multi_state for various ADCM objects.
  - There is support of cluster, service, host, component and providers states
  - This one is allowed to be used in various execution contexts.
options:
  - option-name: type
    required: true
    choises:
      - cluster
      - service
      - provider
      - host
      - component
    description: type of object which should be changed

  - option-name: state
    required: true
    type: string
    description: value of state which should be set

  - option-name: service_name
    required: false
    type: string
    description: useful in cluster and component context only.
    In that context you are able to set the state value for a service belongs to the cluster.

  - option-name: component_name
    required: false
    type: string
    description: useful in cluster and component context only.
    In that context you are able to set the state for a component belongs to the service
"""

EXAMPLES = r"""
- adcm_multi_state_set:
    type: "cluster"
    state: "bimba!"

- adcm_multi_state_set:
    type: "service"
    service_name: "First"
    state: "bimba!"

- adcm_multi_state_set:
    type: "component"
    component_name: "another_component"
    state: "bimba!"

- adcm_multi_state_set:
    type: "component"
    service_name: "another service"
    component_name: "another_component"
    state: "bimba!"
"""

RETURN = r"""
state:
  returned: success
  type: str
  example: "operational"
"""


class ActionModule(ContextActionModule):
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(("type", "service_name", "component_name", "state", "host_id"))
    _MANDATORY_ARGS = ("type", "state")

    def _do_cluster(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(set_cluster_multi_state, context["cluster_id"], self._task.args["state"])
        res["state"] = self._task.args["state"]
        return res

    def _do_service_by_name(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            set_service_multi_state_by_name,
            context["cluster_id"],
            self._task.args["service_name"],
            self._task.args["state"],
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_service(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            set_service_multi_state,
            context["cluster_id"],
            context["service_id"],
            self._task.args["state"],
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_host(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            set_host_multi_state,
            context["host_id"],
            self._task.args["state"],
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_provider(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(set_provider_multi_state, context["provider_id"], self._task.args["state"])
        res["state"] = self._task.args["state"]
        return res

    def _do_host_from_provider(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            set_host_multi_state,
            self._task.args["host_id"],
            self._task.args["state"],
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_component_by_name(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            set_component_multi_state_by_name,
            context["cluster_id"],
            context["service_id"],
            self._task.args["component_name"],
            self._task.args.get("service_name", None),
            self._task.args["state"],
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_component(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            set_component_multi_state,
            context["component_id"],
            self._task.args["state"],
        )
        res["state"] = self._task.args["state"]
        return res
