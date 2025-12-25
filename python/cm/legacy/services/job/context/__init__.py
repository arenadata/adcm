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

"""
Copy-pasted from cm.legacy.services.job.inventory as an alternative development branch for context building for:
- inventory and config.json for ansible
- context for templates

Note that implementations aren't changed or updated significantly => package is not well-designed or truely done.
"""

from cm.legacy.services.job.context._action_process import get_action_process_context
from cm.legacy.services.job.context._base import (
    get_basic_info_for_hosts,
    get_cluster_vars,
    get_inventory_data,
    get_run_context,
    sort_hosts_within_groups,
)
from cm.legacy.services.job.context._config import get_adcm_configuration, get_config_info, get_objects_configurations
from cm.legacy.services.job.context._groups import detect_host_groups_for_cluster_bundle_action
from cm.legacy.services.job.context._imports import get_imports_for_inventory
from cm.legacy.services.job.inventory._types import (
    ClusterNode,
    ClusterVars,
    ComponentNode,
    HostGroupName,
    HostNode,
    ProcessContext,
    ProviderNode,
    ServiceNode,
)

__all__ = [
    "ClusterNode",
    "ClusterVars",
    "ComponentNode",
    "HostGroupName",
    "HostNode",
    "ProcessContext",
    "ProviderNode",
    "ServiceNode",
    "detect_host_groups_for_cluster_bundle_action",
    "get_action_process_context",
    "get_adcm_configuration",
    "get_basic_info_for_hosts",
    "get_cluster_vars",
    "get_config_info",
    "get_imports_for_inventory",
    "get_inventory_data",
    "get_objects_configurations",
    "sort_hosts_within_groups",
    "get_run_context",
]
