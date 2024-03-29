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

from django.urls import path
from rest_framework.routers import SimpleRouter

from api_ui.stack.root import StackUIRoot
from api_ui.stack.views import ClusterPrototypeUIViewSet, ProviderPrototypeUIViewSet

router = SimpleRouter()
router.register("cluster", ClusterPrototypeUIViewSet, basename="cluster")
router.register("provider", ProviderPrototypeUIViewSet, basename="provider")

urlpatterns = [
    path("", StackUIRoot.as_view(), name="root"),
    *router.urls,
]
