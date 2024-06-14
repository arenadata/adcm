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

from api_v2.action.views import ActionHostGroupActionViewSet, ActionViewSet
from api_v2.action_host_group.views import ActionHostGroupViewSet, HostActionHostGroupViewSet
from api_v2.cluster.views import ClusterViewSet
from api_v2.component.views import ComponentViewSet, HostComponentViewSet
from api_v2.config.views import ConfigLogViewSet
from api_v2.group_config.views import GroupConfigViewSet
from api_v2.host.views import HostClusterViewSet, HostGroupConfigViewSet
from api_v2.imports.views import ClusterImportViewSet, ServiceImportViewSet
from api_v2.service.views import ServiceViewSet
from api_v2.upgrade.views import UpgradeViewSet

CLUSTER_PREFIX = ""
ACTION_PREFIX = "actions"
COMPONENT_PREFIX = "components"
HOST_PREFIX = "hosts"
SERVICE_PREFIX = "services"
CONFIG_PREFIX = "configs"
IMPORT_PREFIX = "imports"
CONFIG_GROUPS_PREFIX = "config-groups"
ACTION_HOST_GROUPS_PREFIX = "action-host-groups"


def extract_urls_from_routers(routers: Iterable[NestedSimpleRouter]) -> tuple[str, ...]:
    return tuple(itertools.chain.from_iterable(router.urls for router in routers))


def add_group_config_routers(
    parent_router: NestedSimpleRouter | SimpleRouter, parent_prefix: str, lookup: str
) -> tuple[NestedSimpleRouter, ...]:
    group_config_router = NestedSimpleRouter(parent_router=parent_router, parent_prefix=parent_prefix, lookup=lookup)
    group_config_router.register(
        prefix=CONFIG_GROUPS_PREFIX, viewset=GroupConfigViewSet, basename=f"{lookup}-group-config"
    )

    hosts_router = NestedSimpleRouter(group_config_router, CONFIG_GROUPS_PREFIX, lookup="group_config")
    hosts_router.register(prefix=r"hosts", viewset=HostGroupConfigViewSet, basename=f"{lookup}-group-config-hosts")

    config_router = NestedSimpleRouter(
        parent_router=group_config_router, parent_prefix=CONFIG_GROUPS_PREFIX, lookup="group_config"
    )
    config_router.register(prefix=CONFIG_PREFIX, viewset=ConfigLogViewSet, basename=f"{lookup}-group-config-config")

    return group_config_router, hosts_router, config_router


def add_action_host_groups_routers(
    parent_router: NestedSimpleRouter | SimpleRouter, parent_prefix: str, lookup: str
) -> tuple[NestedSimpleRouter, ...]:
    action_host_groups_router = NestedSimpleRouter(
        parent_router=parent_router, parent_prefix=parent_prefix, lookup=lookup
    )
    action_host_groups_router.register(
        prefix=ACTION_HOST_GROUPS_PREFIX, viewset=ActionHostGroupViewSet, basename=f"{lookup}-action-host-group"
    )

    action_host_groups_actions_router = NestedSimpleRouter(
        parent_router=action_host_groups_router, parent_prefix=ACTION_HOST_GROUPS_PREFIX, lookup="action_host_group"
    )
    action_host_groups_actions_router.register(
        prefix=ACTION_PREFIX, viewset=ActionHostGroupActionViewSet, basename=f"{lookup}-action-host-group-action"
    )

    action_host_groups_hosts_router = NestedSimpleRouter(
        parent_router=action_host_groups_router, parent_prefix=ACTION_HOST_GROUPS_PREFIX, lookup="action_host_group"
    )
    action_host_groups_hosts_router.register(
        prefix=HOST_PREFIX, viewset=HostActionHostGroupViewSet, basename=f"{lookup}-action-host-group-host"
    )

    return action_host_groups_router, action_host_groups_actions_router, action_host_groups_hosts_router


# cluster
cluster_router = SimpleRouter()
cluster_router.register(prefix=CLUSTER_PREFIX, viewset=ClusterViewSet)

import_cluster_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
import_cluster_router.register(prefix=IMPORT_PREFIX, viewset=ClusterImportViewSet, basename="cluster-import")

cluster_action_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
cluster_action_router.register(prefix=ACTION_PREFIX, viewset=ActionViewSet, basename="cluster-action")

cluster_config_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
cluster_config_router.register(prefix=CONFIG_PREFIX, viewset=ConfigLogViewSet, basename="cluster-config")

cluster_config_group_routers = add_group_config_routers(
    parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster"
)

cluster_action_host_groups_routers = add_action_host_groups_routers(
    parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster"
)

# service
service_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
service_router.register(prefix=SERVICE_PREFIX, viewset=ServiceViewSet, basename="service")

import_service_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
import_service_router.register(prefix=IMPORT_PREFIX, viewset=ServiceImportViewSet, basename="service-import")

service_action_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
service_action_router.register(prefix=ACTION_PREFIX, viewset=ActionViewSet, basename="service-action")

service_config_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
service_config_router.register(prefix=CONFIG_PREFIX, viewset=ConfigLogViewSet, basename="service-config")

service_group_config_routers = add_group_config_routers(
    parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service"
)
service_action_host_groups_routers = add_action_host_groups_routers(
    parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service"
)

# component
component_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
component_router.register(prefix=COMPONENT_PREFIX, viewset=ComponentViewSet, basename="component")

component_action_router = NestedSimpleRouter(
    parent_router=component_router, parent_prefix=COMPONENT_PREFIX, lookup="component"
)
component_action_router.register(prefix=ACTION_PREFIX, viewset=ActionViewSet, basename="component-action")

component_config_router = NestedSimpleRouter(
    parent_router=component_router, parent_prefix=COMPONENT_PREFIX, lookup="component"
)
component_config_router.register(prefix=CONFIG_PREFIX, viewset=ConfigLogViewSet, basename="component-config")

component_group_config_routers = add_group_config_routers(
    parent_router=component_router, parent_prefix=COMPONENT_PREFIX, lookup="component"
)
component_action_host_groups_routers = add_action_host_groups_routers(
    parent_router=component_router, parent_prefix=COMPONENT_PREFIX, lookup="component"
)

# host
host_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
host_router.register(prefix=HOST_PREFIX, viewset=HostClusterViewSet, basename="host-cluster")

host_action_router = NestedSimpleRouter(parent_router=host_router, parent_prefix=HOST_PREFIX, lookup="host")
host_action_router.register(prefix=ACTION_PREFIX, viewset=ActionViewSet, basename="host-cluster-action")

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
