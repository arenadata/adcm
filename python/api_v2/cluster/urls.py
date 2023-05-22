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
from api_v2.cluster.views import ClusterViewSet
from api_v2.upgrade.views import UpgradeViewSet
from rest_framework_nested.routers import NestedSimpleRouter, SimpleRouter

router = SimpleRouter()
router.register(prefix="", viewset=ClusterViewSet)

action_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="cluster")
action_router.register(prefix="actions", viewset=ActionViewSet)

upgrade_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="cluster")
upgrade_router.register(prefix="upgrades", viewset=UpgradeViewSet)

urlpatterns = [*router.urls, *action_router.urls, *upgrade_router.urls]
