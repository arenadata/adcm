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

"""RBAC root URLs"""

from django.urls import path, include

from .endpoints import logout, root, token


urlpatterns = [
    path('', root.RBACRoot.as_view(), name='rbac-root'),
    path('user/', include('rbac.endpoints.user.urls')),
    path('group/', include('rbac.endpoints.group_urls')),
    path('role/', include('rbac.endpoints.role_urls')),
    path('logout/', logout.LogOut.as_view(), name='rbac-logout'),
    path('token/', token.GetAuthToken.as_view(), name='rbac-token'),
]
