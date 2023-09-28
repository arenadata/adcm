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
from api_v2.job.views import JobViewSet
from api_v2.log_storage.views import LogStorageJobViewSet
from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

router = SimpleRouter()
router.register("", JobViewSet)

log_storage_router = NestedSimpleRouter(parent_router=router, parent_prefix="", lookup="job")
log_storage_router.register(prefix="logs", viewset=LogStorageJobViewSet, basename="log")

urlpatterns = [*router.urls, *log_storage_router.urls]
