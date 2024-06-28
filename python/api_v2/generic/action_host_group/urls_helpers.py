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

from api_v2.generic.action_host_group.views import (
    ActionHostGroupActionsViewSet,
    ActionHostGroupHostsViewSet,
    ActionHostGroupViewSet,
)

ACTION_PREFIX = "actions"
HOST_PREFIX = "hosts"
ACTION_HOST_GROUPS_PREFIX = "action-host-groups"


def add_action_host_groups_routers(
    ahg_viewset: type[ActionHostGroupViewSet],
    ahg_actions_viewset: type[ActionHostGroupActionsViewSet],
    ahg_hosts_viewset: type[ActionHostGroupHostsViewSet],
    parent_router: NestedSimpleRouter | SimpleRouter,
    parent_prefix: str,
    lookup: str,
) -> tuple[NestedSimpleRouter, ...]:
    action_host_groups_router = NestedSimpleRouter(
        parent_router=parent_router, parent_prefix=parent_prefix, lookup=lookup
    )
    action_host_groups_router.register(
        prefix=ACTION_HOST_GROUPS_PREFIX, viewset=ahg_viewset, basename=f"{lookup}-action-host-group"
    )

    action_host_groups_actions_router = NestedSimpleRouter(
        parent_router=action_host_groups_router, parent_prefix=ACTION_HOST_GROUPS_PREFIX, lookup="action_host_group"
    )
    action_host_groups_actions_router.register(
        prefix=ACTION_PREFIX, viewset=ahg_actions_viewset, basename=f"{lookup}-action-host-group-action"
    )

    action_host_groups_hosts_router = NestedSimpleRouter(
        parent_router=action_host_groups_router, parent_prefix=ACTION_HOST_GROUPS_PREFIX, lookup="action_host_group"
    )
    action_host_groups_hosts_router.register(
        prefix=HOST_PREFIX, viewset=ahg_hosts_viewset, basename=f"{lookup}-action-host-group-host"
    )

    return action_host_groups_router, action_host_groups_actions_router, action_host_groups_hosts_router
