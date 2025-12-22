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

from typing import Iterable
import itertools

from rest_framework_nested.routers import NestedSimpleRouter, SimpleRouter

from api_v2.cluster.views import (
    ClusterActionHostGroupActionsViewSet,
    ClusterActionHostGroupHostsViewSet,
    ClusterActionHostGroupViewSet,
    ClusterActionProcessStepViewSet,
    ClusterActionProcessViewSet,
    ClusterActionViewSet,
    ClusterCHGViewSet,
    ClusterConfigCHGViewSet,
    ClusterConfigViewSet,
    ClusterHostActionProcessStepViewSet,
    ClusterHostActionProcessViewSet,
    ClusterHostActionViewSet,
    ClusterHostCHGViewSet,
    ClusterImportViewSet,
    ClusterUpgradeViewSet,
    ClusterViewSet,
    HostClusterViewSet,
)
from api_v2.component.views import (
    ComponentActionHostGroupActionsViewSet,
    ComponentActionHostGroupHostsViewSet,
    ComponentActionHostGroupViewSet,
    ComponentActionProcessStepViewSet,
    ComponentActionProcessViewSet,
    ComponentActionViewSet,
    ComponentCHGViewSet,
    ComponentConfigCHGViewSet,
    ComponentConfigViewSet,
    ComponentHostCHGViewSet,
    ComponentViewSet,
    HostComponentViewSet,
)
from api_v2.generic.action_host_group.urls_helpers import add_action_host_groups_routers
from api_v2.generic.config_host_group.urls_helpers import add_config_host_group_routers
from api_v2.service.views import (
    ServiceActionHostGroupActionsViewSet,
    ServiceActionHostGroupHostsViewSet,
    ServiceActionHostGroupViewSet,
    ServiceActionProcessStepViewSet,
    ServiceActionProcessViewSet,
    ServiceActionViewSet,
    ServiceCHGViewSet,
    ServiceConfigCHGViewSet,
    ServiceConfigViewSet,
    ServiceHostCHGViewSet,
    ServiceImportViewSet,
    ServiceViewSet,
)

CLUSTER_PREFIX = ""
ACTION_PREFIX = "actions"
COMPONENT_PREFIX = "components"
HOST_PREFIX = "hosts"
SERVICE_PREFIX = "services"
CONFIG_PREFIX = "configs"
IMPORT_PREFIX = "imports"
PROCESS_PREFIX = "processes"
STEP_PREFIX = "steps"


def extract_urls_from_routers(routers: Iterable[NestedSimpleRouter]) -> tuple[str, ...]:
    return tuple(itertools.chain.from_iterable(router.urls for router in routers))


# cluster
cluster_router = SimpleRouter()
cluster_router.register(prefix=CLUSTER_PREFIX, viewset=ClusterViewSet)

import_cluster_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
import_cluster_router.register(prefix=IMPORT_PREFIX, viewset=ClusterImportViewSet, basename="cluster-import")

cluster_action_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
cluster_action_router.register(prefix=ACTION_PREFIX, viewset=ClusterActionViewSet, basename="cluster-action")

cluster_action_process_router = NestedSimpleRouter(
    parent_router=cluster_action_router, parent_prefix=ACTION_PREFIX, lookup="action"
)
cluster_action_process_router.register(
    prefix=PROCESS_PREFIX, viewset=ClusterActionProcessViewSet, basename="cluster-action-process"
)

cluster_action_process_step_router = NestedSimpleRouter(
    parent_router=cluster_action_process_router, parent_prefix=PROCESS_PREFIX, lookup="process"
)
cluster_action_process_step_router.register(
    prefix=STEP_PREFIX, viewset=ClusterActionProcessStepViewSet, basename="cluster-action-process-step"
)

cluster_config_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
cluster_config_router.register(prefix=CONFIG_PREFIX, viewset=ClusterConfigViewSet, basename="cluster-config")

cluster_config_group_routers = add_config_host_group_routers(
    chg_viewset=ClusterCHGViewSet,
    host_chg_viewset=ClusterHostCHGViewSet,
    config_chg_viewset=ClusterConfigCHGViewSet,
    parent_router=cluster_router,
    parent_prefix=CLUSTER_PREFIX,
    lookup="cluster",
)

cluster_action_host_groups_routers = add_action_host_groups_routers(
    ahg_viewset=ClusterActionHostGroupViewSet,
    ahg_hosts_viewset=ClusterActionHostGroupHostsViewSet,
    ahg_actions_viewset=ClusterActionHostGroupActionsViewSet,
    parent_router=cluster_router,
    parent_prefix=CLUSTER_PREFIX,
    lookup="cluster",
)

# service
service_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
service_router.register(prefix=SERVICE_PREFIX, viewset=ServiceViewSet, basename="service")

import_service_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
import_service_router.register(prefix=IMPORT_PREFIX, viewset=ServiceImportViewSet, basename="service-import")

service_action_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
service_action_router.register(prefix=ACTION_PREFIX, viewset=ServiceActionViewSet, basename="service-action")

service_config_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
service_config_router.register(prefix=CONFIG_PREFIX, viewset=ServiceConfigViewSet, basename="service-config")

service_chg_routers = add_config_host_group_routers(
    chg_viewset=ServiceCHGViewSet,
    host_chg_viewset=ServiceHostCHGViewSet,
    config_chg_viewset=ServiceConfigCHGViewSet,
    parent_router=service_router,
    parent_prefix=SERVICE_PREFIX,
    lookup="service",
)
service_action_host_groups_routers = add_action_host_groups_routers(
    ahg_viewset=ServiceActionHostGroupViewSet,
    ahg_hosts_viewset=ServiceActionHostGroupHostsViewSet,
    ahg_actions_viewset=ServiceActionHostGroupActionsViewSet,
    parent_router=service_router,
    parent_prefix=SERVICE_PREFIX,
    lookup="service",
)
service_action_process_router = NestedSimpleRouter(
    parent_router=service_action_router, parent_prefix=ACTION_PREFIX, lookup="action"
)
service_action_process_router.register(
    prefix=PROCESS_PREFIX, viewset=ServiceActionProcessViewSet, basename="service-action-process"
)

service_action_process_step_router = NestedSimpleRouter(
    parent_router=service_action_process_router, parent_prefix=PROCESS_PREFIX, lookup="process"
)
service_action_process_step_router.register(
    prefix=STEP_PREFIX, viewset=ServiceActionProcessStepViewSet, basename="service-action-process-step"
)

# component
component_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
component_router.register(prefix=COMPONENT_PREFIX, viewset=ComponentViewSet, basename="component")

component_action_router = NestedSimpleRouter(
    parent_router=component_router, parent_prefix=COMPONENT_PREFIX, lookup="component"
)
component_action_router.register(prefix=ACTION_PREFIX, viewset=ComponentActionViewSet, basename="component-action")

component_config_router = NestedSimpleRouter(
    parent_router=component_router, parent_prefix=COMPONENT_PREFIX, lookup="component"
)
component_config_router.register(prefix=CONFIG_PREFIX, viewset=ComponentConfigViewSet, basename="component-config")

component_chg_routers = add_config_host_group_routers(
    chg_viewset=ComponentCHGViewSet,
    host_chg_viewset=ComponentHostCHGViewSet,
    config_chg_viewset=ComponentConfigCHGViewSet,
    parent_router=component_router,
    parent_prefix=COMPONENT_PREFIX,
    lookup="component",
)
component_action_host_groups_routers = add_action_host_groups_routers(
    ahg_viewset=ComponentActionHostGroupViewSet,
    ahg_hosts_viewset=ComponentActionHostGroupHostsViewSet,
    ahg_actions_viewset=ComponentActionHostGroupActionsViewSet,
    parent_router=component_router,
    parent_prefix=COMPONENT_PREFIX,
    lookup="component",
)
component_action_process_router = NestedSimpleRouter(
    parent_router=component_action_router, parent_prefix=ACTION_PREFIX, lookup="action"
)
component_action_process_router.register(
    prefix=PROCESS_PREFIX, viewset=ComponentActionProcessViewSet, basename="component-action-process"
)

component_action_process_step_router = NestedSimpleRouter(
    parent_router=component_action_process_router, parent_prefix=PROCESS_PREFIX, lookup="process"
)
component_action_process_step_router.register(
    prefix=STEP_PREFIX, viewset=ComponentActionProcessStepViewSet, basename="component-action-process-step"
)

# host
host_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
host_router.register(prefix=HOST_PREFIX, viewset=HostClusterViewSet, basename="host-cluster")

host_action_router = NestedSimpleRouter(parent_router=host_router, parent_prefix=HOST_PREFIX, lookup="host")
host_action_router.register(prefix=ACTION_PREFIX, viewset=ClusterHostActionViewSet, basename="host-cluster-action")

host_action_process_router = NestedSimpleRouter(
    parent_router=host_action_router, parent_prefix=ACTION_PREFIX, lookup="action"
)
host_action_process_router.register(
    prefix=PROCESS_PREFIX, viewset=ClusterHostActionProcessViewSet, basename="host-cluster-action-process"
)

host_action_process_step_router = NestedSimpleRouter(
    parent_router=host_action_process_router, parent_prefix=PROCESS_PREFIX, lookup="process"
)
host_action_process_step_router.register(
    prefix=STEP_PREFIX, viewset=ClusterHostActionProcessStepViewSet, basename="host-cluster-action-process-step"
)

host_component_router = NestedSimpleRouter(parent_router=host_router, parent_prefix=HOST_PREFIX, lookup="host")
host_component_router.register(prefix=COMPONENT_PREFIX, viewset=HostComponentViewSet, basename="host-cluster-component")

# other
upgrade_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
upgrade_router.register(prefix="upgrades", viewset=ClusterUpgradeViewSet)


urlpatterns = [
    # cluster
    *cluster_router.urls,
    *cluster_action_router.urls,
    *cluster_action_process_router.urls,
    *cluster_action_process_step_router.urls,
    *cluster_config_router.urls,
    *import_cluster_router.urls,
    *extract_urls_from_routers(cluster_config_group_routers),
    *extract_urls_from_routers(cluster_action_host_groups_routers),
    # service
    *service_router.urls,
    *service_action_router.urls,
    *service_action_process_router.urls,
    *service_action_process_step_router.urls,
    *service_config_router.urls,
    *import_service_router.urls,
    *extract_urls_from_routers(service_chg_routers),
    *extract_urls_from_routers(service_action_host_groups_routers),
    # component
    *component_router.urls,
    *component_action_router.urls,
    *component_action_process_router.urls,
    *component_action_process_step_router.urls,
    *component_config_router.urls,
    *extract_urls_from_routers(component_chg_routers),
    *extract_urls_from_routers(component_action_host_groups_routers),
    # host
    *host_router.urls,
    *host_action_router.urls,
    *host_action_process_router.urls,
    *host_action_process_step_router.urls,
    *host_component_router.urls,
    # other
    *upgrade_router.urls,
]
