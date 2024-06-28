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

from rest_framework_nested.routers import NestedSimpleRouter, SimpleRouter

from api_v2.config.views import ConfigLogViewSet
from api_v2.host.views import HostActionViewSet, HostViewSet

host_router = SimpleRouter()
host_router.register(prefix="", viewset=HostViewSet)

host_config_router = NestedSimpleRouter(parent_router=host_router, parent_prefix="", lookup="host")
host_config_router.register(prefix="configs", viewset=ConfigLogViewSet, basename="host-config")

host_action_router = NestedSimpleRouter(parent_router=host_router, parent_prefix="", lookup="host")
host_action_router.register(prefix="actions", viewset=HostActionViewSet, basename="host-action")

urlpatterns = [
    *host_router.urls,
    *host_config_router.urls,
    *host_action_router.urls,
]
