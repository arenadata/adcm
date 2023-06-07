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
from api_v2.prototype.views import AcceptLicenseViewSet, PrototypeViewSet
from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

router = SimpleRouter()
router.register("", PrototypeViewSet)

prototype_license_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="prototype")
prototype_license_router.register(prefix="license", viewset=AcceptLicenseViewSet, basename="license")

urlpatterns = [*router.urls, *prototype_license_router.urls]
