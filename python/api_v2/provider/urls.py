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
from api_v2.provider.views import (
    ProviderActionViewSet,
    ProviderCHGViewSet,
    ProviderConfigCHGViewSet,
    ProviderConfigViewSet,
    ProviderHostCHGViewSet,
    ProviderUpgradeViewSet,
    ProviderViewSet,
)


def extract_urls_from_routers(routers: Iterable[NestedSimpleRouter]) -> tuple[str, ...]:
    return tuple(itertools.chain.from_iterable(router.urls for router in routers))


router = SimpleRouter()
router.register("", ProviderViewSet)

action_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="provider")
action_router.register(prefix="actions", viewset=ProviderActionViewSet, basename="provider-action")

config_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="provider")
config_router.register(prefix="configs", viewset=ProviderConfigViewSet, basename="provider-config")

upgrade_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="provider")
upgrade_router.register(prefix="upgrades", viewset=ProviderUpgradeViewSet)


config_host_group_routers = add_config_host_group_routers(
    chg_viewset=ProviderCHGViewSet,
    host_chg_viewset=ProviderHostCHGViewSet,
    config_chg_viewset=ProviderConfigCHGViewSet,
    parent_router=router,
    parent_prefix="",
    lookup="provider",
)

urlpatterns = [
    *router.urls,
    *action_router.urls,
    *config_router.urls,
    *upgrade_router.urls,
    *extract_urls_from_routers(config_host_group_routers),
]
