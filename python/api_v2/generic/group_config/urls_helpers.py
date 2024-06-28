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
from api_v2.generic.group_config.views import GroupConfigViewSet, HostGroupConfigViewSet

CONFIG_PREFIX = "configs"
CONFIG_GROUPS_PREFIX = "config-groups"


def add_group_config_routers(
    group_config_viewset: type[GroupConfigViewSet],
    host_group_config_viewset: type[HostGroupConfigViewSet],
    config_group_config_viewset: type[ConfigLogViewSet],
    parent_router: NestedSimpleRouter | SimpleRouter,
    parent_prefix: str,
    lookup: str,
) -> tuple[NestedSimpleRouter, ...]:
    group_config_router = NestedSimpleRouter(parent_router=parent_router, parent_prefix=parent_prefix, lookup=lookup)
    group_config_router.register(
        prefix=CONFIG_GROUPS_PREFIX, viewset=group_config_viewset, basename=f"{lookup}-group-config"
    )

    hosts_router = NestedSimpleRouter(group_config_router, CONFIG_GROUPS_PREFIX, lookup="group_config")
    hosts_router.register(prefix="hosts", viewset=host_group_config_viewset, basename=f"{lookup}-group-config-hosts")

    config_router = NestedSimpleRouter(
        parent_router=group_config_router, parent_prefix=CONFIG_GROUPS_PREFIX, lookup="group_config"
    )
    config_router.register(
        prefix=CONFIG_PREFIX, viewset=config_group_config_viewset, basename=f"{lookup}-group-config-config"
    )

    return group_config_router, hosts_router, config_router
