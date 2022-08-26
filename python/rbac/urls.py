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

from django.urls import include, path

from rbac.endpoints.logout import LogOut
from rbac.endpoints.root import RBACRoot
from rbac.endpoints.token import GetAuthToken

urlpatterns = [
    path('', RBACRoot.as_view(), name='root'),
    path('me/', include('rbac.endpoints.me.urls')),
    path('user/', include('rbac.endpoints.user.urls')),
    path('group/', include('rbac.endpoints.group.urls')),
    path('role/', include('rbac.endpoints.role.urls')),
    path(r'policy/', include('rbac.endpoints.policy.urls')),
    path('logout/', LogOut.as_view(), name='logout'),
    path('token/', GetAuthToken.as_view(), name='token'),
]
