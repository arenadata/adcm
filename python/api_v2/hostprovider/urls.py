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
from api_v2.config.views import ConfigLogViewSet
from api_v2.group_config.views import GroupConfigViewSet
from api_v2.host.views import HostGroupConfigViewSet
from api_v2.hostprovider.views import HostProviderViewSet
from api_v2.upgrade.views import UpgradeViewSet
from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

CONFIG_GROUPS_PREFIX = "config-groups"

router = SimpleRouter()
router.register("", HostProviderViewSet)

action_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="hostprovider")
action_router.register(prefix="actions", viewset=ActionViewSet, basename="provider-action")

config_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="hostprovider")
config_router.register(prefix="configs", viewset=ConfigLogViewSet, basename="provider-config")

upgrade_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="hostprovider")
upgrade_router.register(prefix="upgrades", viewset=UpgradeViewSet)

group_config_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="hostprovider")
group_config_router.register(
    prefix=CONFIG_GROUPS_PREFIX, viewset=GroupConfigViewSet, basename="hostprovider-group-config"
)

group_config_hosts_router = NestedSimpleRouter(group_config_router, CONFIG_GROUPS_PREFIX, lookup="group_config")
group_config_hosts_router.register(
    prefix=r"hosts", viewset=HostGroupConfigViewSet, basename="hostprovider-group-config-hosts"
)

group_config_config_router = NestedSimpleRouter(
    parent_router=group_config_router, parent_prefix=CONFIG_GROUPS_PREFIX, lookup="group_config"
)
group_config_config_router.register(
    prefix="configs", viewset=ConfigLogViewSet, basename="hostprovider-group-config-config"
)

urlpatterns = [
    *router.urls,
    *action_router.urls,
    *config_router.urls,
    *upgrade_router.urls,
    *group_config_router.urls,
    *group_config_hosts_router.urls,
    *group_config_config_router.urls,
]
