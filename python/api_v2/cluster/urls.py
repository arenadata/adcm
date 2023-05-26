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

from api_v2.action.views import ClusterActionViewSet as CommonActionViewSet
from api_v2.action.views import ServiceActionViewSet
from api_v2.cluster.views import ClusterViewSet, MappingViewSet
from api_v2.config.views import ConfigLogViewSet
from api_v2.host.views import HostViewSet
from api_v2.service.views import ServiceViewSet
from api_v2.upgrade.views import UpgradeViewSet
from rest_framework_nested.routers import NestedSimpleRouter, SimpleRouter

ACTION_ROUTER_PREFIX = "actions"
CLUSTER_ROUTER_PREFIX = ""
HOST_ROUTER_PREFIX = "hosts"
SERVICE_ROUTER_PREFIX = "services"

router = SimpleRouter()
router.register(prefix=CLUSTER_ROUTER_PREFIX, viewset=ClusterViewSet)

cluster_action_router = NestedSimpleRouter(parent_router=router, parent_prefix=CLUSTER_ROUTER_PREFIX, lookup="cluster")
cluster_action_router.register(prefix=ACTION_ROUTER_PREFIX, viewset=CommonActionViewSet)

upgrade_router = NestedSimpleRouter(parent_router=router, parent_prefix=CLUSTER_ROUTER_PREFIX, lookup="cluster")
upgrade_router.register(prefix="upgrades", viewset=UpgradeViewSet)

mapping_router = NestedSimpleRouter(parent_router=router, parent_prefix=CLUSTER_ROUTER_PREFIX, lookup="cluster")
mapping_router.register(prefix="mapping", viewset=MappingViewSet, basename="mapping")

service_router = NestedSimpleRouter(parent_router=router, parent_prefix=CLUSTER_ROUTER_PREFIX, lookup="cluster")
service_router.register(prefix=SERVICE_ROUTER_PREFIX, viewset=ServiceViewSet)

service_action_router = NestedSimpleRouter(
    parent_router=service_router, parent_prefix=SERVICE_ROUTER_PREFIX, lookup="service"
)
service_action_router.register(prefix=ACTION_ROUTER_PREFIX, viewset=ServiceActionViewSet)

host_router = NestedSimpleRouter(parent_router=router, parent_prefix=CLUSTER_ROUTER_PREFIX, lookup="cluster")
host_router.register(prefix=HOST_ROUTER_PREFIX, viewset=HostViewSet)

host_action_router = NestedSimpleRouter(parent_router=host_router, parent_prefix=HOST_ROUTER_PREFIX, lookup="host")
host_action_router.register(prefix=ACTION_ROUTER_PREFIX, viewset=CommonActionViewSet)

cluster_config_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="cluster")
cluster_config_router.register(prefix="configs", viewset=ConfigLogViewSet, basename="cluster-config")

service_config_router = NestedSimpleRouter(parent_router=service_router, parent_prefix="services", lookup="service")
service_config_router.register(prefix="configs", viewset=ConfigLogViewSet, basename="service-config")

urlpatterns = [
    *router.urls,
    *cluster_action_router.urls,
    *upgrade_router.urls,
    *mapping_router.urls,
    *service_router.urls,
    *service_action_router.urls,
    *host_router.urls,
    *host_action_router.urls,
    *cluster_config_router.urls,
    *service_config_router.urls,
]
