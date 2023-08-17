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

from api_v2.rbac.groups.urls import group_router
from api_v2.rbac.role.views import RoleViewSet
from api_v2.rbac.users.urls import user_router
from api_v2.rbac.views import RbacRoot
from django.urls import path
from rest_framework.routers import SimpleRouter

role_router = SimpleRouter()
role_router.register("roles", RoleViewSet)
urlpatterns = [
    path("", RbacRoot.as_view(), name="root"),
    *role_router.urls,
    *user_router.urls,
    *group_router.urls,
]
