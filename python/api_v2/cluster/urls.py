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
    ClusterActionViewSet,
    ClusterConfigHostGroupViewSet,
    ClusterConfigViewSet,
    ClusterGroupConfigViewSet,
    ClusterHostActionViewSet,
    ClusterHostGroupConfigViewSet,
    ClusterImportViewSet,
    ClusterViewSet,
    HostClusterViewSet,
)
from api_v2.component.views import (
    ComponentActionHostGroupActionsViewSet,
    ComponentActionHostGroupHostsViewSet,
    ComponentActionHostGroupViewSet,
    ComponentActionViewSet,
    ComponentConfigHostGroupViewSet,
    ComponentConfigViewSet,
    ComponentGroupConfigViewSet,
    ComponentHostGroupConfigViewSet,
    ComponentViewSet,
    HostComponentViewSet,
)
from api_v2.generic.action_host_group.urls_helpers import add_action_host_groups_routers
from api_v2.generic.group_config.urls_helpers import add_group_config_routers
from api_v2.service.views import (
    ServiceActionHostGroupActionsViewSet,
    ServiceActionHostGroupHostsViewSet,
    ServiceActionHostGroupViewSet,
    ServiceActionViewSet,
    ServiceConfigHostGroupViewSet,
    ServiceConfigViewSet,
    ServiceGroupConfigViewSet,
    ServiceHostGroupConfigViewSet,
    ServiceImportViewSet,
    ServiceViewSet,
)
from api_v2.upgrade.views import UpgradeViewSet

CLUSTER_PREFIX = ""
ACTION_PREFIX = "actions"
COMPONENT_PREFIX = "components"
HOST_PREFIX = "hosts"
SERVICE_PREFIX = "services"
CONFIG_PREFIX = "configs"
IMPORT_PREFIX = "imports"


def extract_urls_from_routers(routers: Iterable[NestedSimpleRouter]) -> tuple[str, ...]:
    return tuple(itertools.chain.from_iterable(router.urls for router in routers))


# cluster
cluster_router = SimpleRouter()
cluster_router.register(prefix=CLUSTER_PREFIX, viewset=ClusterViewSet)

import_cluster_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
import_cluster_router.register(prefix=IMPORT_PREFIX, viewset=ClusterImportViewSet, basename="cluster-import")

cluster_action_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
cluster_action_router.register(prefix=ACTION_PREFIX, viewset=ClusterActionViewSet, basename="cluster-action")

cluster_config_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
cluster_config_router.register(prefix=CONFIG_PREFIX, viewset=ClusterConfigViewSet, basename="cluster-config")

cluster_config_group_routers = add_group_config_routers(
    group_config_viewset=ClusterGroupConfigViewSet,
    host_group_config_viewset=ClusterHostGroupConfigViewSet,
    config_group_config_viewset=ClusterConfigHostGroupViewSet,
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

service_group_config_routers = add_group_config_routers(
    group_config_viewset=ServiceGroupConfigViewSet,
    host_group_config_viewset=ServiceHostGroupConfigViewSet,
    config_group_config_viewset=ServiceConfigHostGroupViewSet,
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

component_group_config_routers = add_group_config_routers(
    group_config_viewset=ComponentGroupConfigViewSet,
    host_group_config_viewset=ComponentHostGroupConfigViewSet,
    config_group_config_viewset=ComponentConfigHostGroupViewSet,
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

# host
host_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
host_router.register(prefix=HOST_PREFIX, viewset=HostClusterViewSet, basename="host-cluster")

host_action_router = NestedSimpleRouter(parent_router=host_router, parent_prefix=HOST_PREFIX, lookup="host")
host_action_router.register(prefix=ACTION_PREFIX, viewset=ClusterHostActionViewSet, basename="host-cluster-action")

host_component_router = NestedSimpleRouter(parent_router=host_router, parent_prefix=HOST_PREFIX, lookup="host")
host_component_router.register(prefix=COMPONENT_PREFIX, viewset=HostComponentViewSet, basename="host-cluster-component")

# other
upgrade_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
upgrade_router.register(prefix="upgrades", viewset=UpgradeViewSet)


urlpatterns = [
    # cluster
    *cluster_router.urls,
    *cluster_action_router.urls,
    *cluster_config_router.urls,
    *import_cluster_router.urls,
    *extract_urls_from_routers(cluster_config_group_routers),
    *extract_urls_from_routers(cluster_action_host_groups_routers),
    # service
    *service_router.urls,
    *service_action_router.urls,
    *service_config_router.urls,
    *import_service_router.urls,
    *extract_urls_from_routers(service_group_config_routers),
    *extract_urls_from_routers(service_action_host_groups_routers),
    # component
    *component_router.urls,
    *component_action_router.urls,
    *component_config_router.urls,
    *extract_urls_from_routers(component_group_config_routers),
    *extract_urls_from_routers(component_action_host_groups_routers),
    # host
    *host_router.urls,
    *host_action_router.urls,
    *host_component_router.urls,
    # other
    *upgrade_router.urls,
]
