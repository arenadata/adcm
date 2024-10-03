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

from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from api_v2.generic.config_host_group.urls_helpers import add_config_host_group_routers
from api_v2.hostprovider.views import (
    HostProviderActionViewSet,
    HostProviderCHGViewSet,
    HostProviderConfigCHGViewSet,
    HostProviderConfigViewSet,
    HostProviderHostCHGViewSet,
    HostProviderUpgradeViewSet,
    HostProviderViewSet,
)

CONFIG_GROUPS_PREFIX = "config-groups"


def extract_urls_from_routers(routers: Iterable[NestedSimpleRouter]) -> tuple[str, ...]:
    return tuple(itertools.chain.from_iterable(router.urls for router in routers))


router = SimpleRouter()
router.register("", HostProviderViewSet)

action_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="hostprovider")
action_router.register(prefix="actions", viewset=HostProviderActionViewSet, basename="provider-action")

config_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="hostprovider")
config_router.register(prefix="configs", viewset=HostProviderConfigViewSet, basename="provider-config")

upgrade_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="hostprovider")
upgrade_router.register(prefix="upgrades", viewset=HostProviderUpgradeViewSet)


config_host_group_routers = add_config_host_group_routers(
    chg_viewset=HostProviderCHGViewSet,
    host_chg_viewset=HostProviderHostCHGViewSet,
    config_chg_viewset=HostProviderConfigCHGViewSet,
    parent_router=router,
    parent_prefix="",
    lookup="hostprovider",
)

urlpatterns = [
    *router.urls,
    *action_router.urls,
    *config_router.urls,
    *upgrade_router.urls,
    *extract_urls_from_routers(config_host_group_routers),
]
