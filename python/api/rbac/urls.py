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

from django.urls import include, path

from api.rbac.logout import LogOut
from api.rbac.root import RBACRoot
from api.rbac.token import GetAuthToken

urlpatterns = [
    path("", RBACRoot.as_view(), name="root"),
    path("me/", include("api.rbac.me.urls")),
    path("user/", include("api.rbac.user.urls")),
    path("group/", include("api.rbac.group.urls")),
    path("role/", include("api.rbac.role.urls")),
    path("policy/", include("api.rbac.policy.urls")),
    path("logout/", LogOut.as_view(), name="logout"),
    path("token/", GetAuthToken.as_view(), name="token"),
]
