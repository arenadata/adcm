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

from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from api_v2.generic.config.views import ConfigLogViewSet
from api_v2.generic.config_host_group.views import CHGViewSet, HostCHGViewSet

CONFIG_PREFIX = "configs"
CONFIG_GROUPS_PREFIX = "config-groups"


def add_config_host_group_routers(
    chg_viewset: type[CHGViewSet],
    host_chg_viewset: type[HostCHGViewSet],
    config_chg_viewset: type[ConfigLogViewSet],
    parent_router: NestedSimpleRouter | SimpleRouter,
    parent_prefix: str,
    lookup: str,
) -> tuple[NestedSimpleRouter, ...]:
    host_group_router = NestedSimpleRouter(parent_router=parent_router, parent_prefix=parent_prefix, lookup=lookup)
    host_group_router.register(prefix=CONFIG_GROUPS_PREFIX, viewset=chg_viewset, basename=f"{lookup}-group-config")

    hosts_router = NestedSimpleRouter(host_group_router, CONFIG_GROUPS_PREFIX, lookup="config_host_group")
    hosts_router.register(prefix="hosts", viewset=host_chg_viewset, basename=f"{lookup}-group-config-hosts")

    config_router = NestedSimpleRouter(
        parent_router=host_group_router, parent_prefix=CONFIG_GROUPS_PREFIX, lookup="config_host_group"
    )
    config_router.register(prefix=CONFIG_PREFIX, viewset=config_chg_viewset, basename=f"{lookup}-group-config-config")

    return host_group_router, hosts_router, config_router
