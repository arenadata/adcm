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

from ansible_plugin.utils import (
    ContextActionModule,
    unset_cluster_multi_state,
    unset_component_multi_state,
    unset_component_multi_state_by_name,
    unset_host_multi_state,
    unset_provider_multi_state,
    unset_service_multi_state,
    unset_service_multi_state_by_name,
)

ANSIBLE_METADATA = {"metadata_version": "1.1", "supported_by": "Arenadata"}

DOCUMENTATION = r"""
---
module: adcm_multi_state_set
short_description: Unset one state from multi_state field and raise Error
description:
  - This is special ADCM only module which is useful for deleting multi_state from various ADCM objects.
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

  - option-name: missing_ok
    required: false
    type: boolean
    default: false
    description: if missing_ok is true then we should not rise any exception if there is no such multi state on object
"""

EXAMPLES = r"""
- adcm_multi_state_unset:
    type: "cluster"
    state: "bimba!"

- adcm_multi_state_unset:
    type: "service"
    service_name: "First"
    state: "bimba!"

- adcm_multi_state_unset:
    type: "component"
    component_name: "another_component"
    state: "bimba!"

- adcm_multi_state_unset:
    type: "component"
    service_name: "another service"
    component_name: "another_component"
    state: "bimba!"
    missing_ok: true ## false is default value of this parameter if parameter is absent
"""

RETURN = r"""
state:
  returned: success
  type: str
  example: "operational"
"""


class ActionModule(ContextActionModule):
    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(("type", "service_name", "component_name", "state", "missing_ok", "host_id"))
    _MANDATORY_ARGS = ("type", "state")

    def _do_cluster(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            unset_cluster_multi_state,
            context["cluster_id"],
            self._task.args["state"],
            self._task.args.get("missing_ok", False),
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_service_by_name(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            unset_service_multi_state_by_name,
            context["cluster_id"],
            self._task.args["service_name"],
            self._task.args["state"],
            self._task.args.get("missing_ok", False),
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_service(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            unset_service_multi_state,
            context["cluster_id"],
            context["service_id"],
            self._task.args["state"],
            self._task.args.get("missing_ok", False),
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_host(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            unset_host_multi_state,
            context["host_id"],
            self._task.args["state"],
            self._task.args.get("missing_ok", False),
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_provider(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            unset_provider_multi_state,
            context["provider_id"],
            self._task.args["state"],
            self._task.args.get("missing_ok", False),
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_host_from_provider(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            unset_host_multi_state,
            self._task.args["host_id"],
            self._task.args["state"],
            self._task.args.get("missing_ok", False),
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_component_by_name(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            unset_component_multi_state_by_name,
            context["cluster_id"],
            context["service_id"],
            self._task.args["component_name"],
            self._task.args.get("service_name", None),
            self._task.args["state"],
            self._task.args.get("missing_ok", False),
        )
        res["state"] = self._task.args["state"]
        return res

    def _do_component(self, task_vars, context):  # noqa: ARG002
        res = self._wrap_call(
            unset_component_multi_state,
            context["component_id"],
            self._task.args["state"],
            self._task.args.get("missing_ok", False),
        )
        res["state"] = self._task.args["state"]
        return res
