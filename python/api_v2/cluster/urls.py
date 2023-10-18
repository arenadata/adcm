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

from api_v2.action.views import ActionViewSet
from api_v2.cluster.views import ClusterViewSet, MappingViewSet
from api_v2.component.views import ComponentViewSet, HostComponentViewSet
from api_v2.config.views import ConfigLogViewSet
from api_v2.group_config.views import GroupConfigViewSet
from api_v2.host.views import HostClusterViewSet, HostGroupConfigViewSet
from api_v2.imports.views import ImportViewSet
from api_v2.service.views import ServiceViewSet
from api_v2.upgrade.views import UpgradeViewSet
from rest_framework_nested.routers import NestedSimpleRouter, SimpleRouter

CLUSTER_PREFIX = ""
ACTION_PREFIX = "actions"
COMPONENT_PREFIX = "components"
HOST_PREFIX = "hosts"
SERVICE_PREFIX = "services"
CONFIG_PREFIX = "configs"
IMPORT_PREFIX = "imports"
CONFIG_GROUPS_PREFIX = "config-groups"

# cluster
cluster_router = SimpleRouter()
cluster_router.register(prefix=CLUSTER_PREFIX, viewset=ClusterViewSet)

cluster_action_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
cluster_action_router.register(prefix=ACTION_PREFIX, viewset=ActionViewSet, basename="cluster-action")

cluster_config_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
cluster_config_router.register(prefix=CONFIG_PREFIX, viewset=ConfigLogViewSet, basename="cluster-config")

cluster_group_config_router = NestedSimpleRouter(
    parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster"
)
cluster_group_config_router.register(
    prefix=CONFIG_GROUPS_PREFIX, viewset=GroupConfigViewSet, basename="cluster-group-config"
)
cluster_group_config_hosts_router = NestedSimpleRouter(
    cluster_group_config_router, CONFIG_GROUPS_PREFIX, lookup="group_config"
)
cluster_group_config_hosts_router.register(
    prefix=r"hosts", viewset=HostGroupConfigViewSet, basename="cluster-group-config-hosts"
)

cluster_group_config_config_router = NestedSimpleRouter(
    parent_router=cluster_group_config_router, parent_prefix=CONFIG_GROUPS_PREFIX, lookup="group_config"
)
cluster_group_config_config_router.register(
    prefix=CONFIG_PREFIX, viewset=ConfigLogViewSet, basename="cluster-group-config-config"
)
import_cluster_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
import_cluster_router.register(prefix=IMPORT_PREFIX, viewset=ImportViewSet, basename="cluster-import")

# service
service_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
service_router.register(prefix=SERVICE_PREFIX, viewset=ServiceViewSet, basename="service")

service_action_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
service_action_router.register(prefix=ACTION_PREFIX, viewset=ActionViewSet, basename="service-action")

service_config_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
service_config_router.register(prefix=CONFIG_PREFIX, viewset=ConfigLogViewSet, basename="service-config")

service_group_config_router = NestedSimpleRouter(
    parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service"
)
service_group_config_router.register(
    prefix=CONFIG_GROUPS_PREFIX, viewset=GroupConfigViewSet, basename="service-group-config"
)

service_group_config_config_router = NestedSimpleRouter(
    parent_router=service_group_config_router, parent_prefix=CONFIG_GROUPS_PREFIX, lookup="group_config"
)
service_group_config_config_router.register(
    prefix=CONFIG_PREFIX, viewset=ConfigLogViewSet, basename="service-group-config-config"
)
service_group_config_hosts_router = NestedSimpleRouter(
    service_group_config_router, CONFIG_GROUPS_PREFIX, lookup="group_config"
)
service_group_config_hosts_router.register(
    prefix=r"hosts", viewset=HostGroupConfigViewSet, basename="service-group-config-hosts"
)
import_service_router = NestedSimpleRouter(parent_router=service_router, parent_prefix=SERVICE_PREFIX, lookup="service")
import_service_router.register(prefix=IMPORT_PREFIX, viewset=ImportViewSet, basename="service-import")

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

component_group_config_router = NestedSimpleRouter(
    parent_router=component_router, parent_prefix=COMPONENT_PREFIX, lookup="component"
)
component_group_config_router.register(
    prefix=CONFIG_GROUPS_PREFIX, viewset=GroupConfigViewSet, basename="component-group-config"
)

component_group_config_config_router = NestedSimpleRouter(
    parent_router=component_group_config_router, parent_prefix=CONFIG_GROUPS_PREFIX, lookup="group_config"
)
component_group_config_config_router.register(
    prefix=CONFIG_PREFIX, viewset=ConfigLogViewSet, basename="component-group-config-config"
)
component_group_config_hosts_router = NestedSimpleRouter(
    component_group_config_router, CONFIG_GROUPS_PREFIX, lookup="group_config"
)
component_group_config_hosts_router.register(
    prefix=r"hosts", viewset=HostGroupConfigViewSet, basename="component-group-config-hosts"
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

mapping_router = NestedSimpleRouter(parent_router=cluster_router, parent_prefix=CLUSTER_PREFIX, lookup="cluster")
mapping_router.register(prefix="mapping", viewset=MappingViewSet, basename="mapping")


urlpatterns = [
    # cluster
    *cluster_router.urls,
    *cluster_action_router.urls,
    *cluster_config_router.urls,
    *cluster_group_config_router.urls,
    *cluster_group_config_config_router.urls,
    *cluster_group_config_hosts_router.urls,
    *import_cluster_router.urls,
    # service
    *service_router.urls,
    *service_action_router.urls,
    *service_config_router.urls,
    *service_group_config_router.urls,
    *service_group_config_config_router.urls,
    *service_group_config_hosts_router.urls,
    *import_service_router.urls,
    # component
    *component_router.urls,
    *component_action_router.urls,
    *component_config_router.urls,
    *component_group_config_router.urls,
    *component_group_config_config_router.urls,
    *component_group_config_hosts_router.urls,
    # host
    *host_router.urls,
    *host_action_router.urls,
    *host_component_router.urls,
    # other
    *upgrade_router.urls,
    *mapping_router.urls,
]
