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

"""User URL's"""

from django.urls import path, include

from .views import UserViewSet, UserGroupViewSet, UserRoleViewSet, ChangePassword


role_urls = [
    path('', UserRoleViewSet.as_view({'get': 'list', 'post': 'create'}), name='user-role-list'),
    path(
        '<int:role_id>/',
        UserRoleViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
        name='user-role-detail',
    ),
]

group_urls = [
    path('', UserGroupViewSet.as_view({'get': 'list', 'post': 'create'}), name='user-group-list'),
    path(
        '<int:group_id>/',
        UserGroupViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
        name='user-group-detail',
    ),
]

urlpatterns = [
    path('', UserViewSet.as_view({'get': 'list', 'post': 'create'}), name='user-list'),
    path(
        '<int:id>/',
        include(
            [
                path(
                    '',
                    UserViewSet.as_view(
                        {'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}
                    ),
                    name='user-detail',
                ),
                path('change_password/', ChangePassword.as_view(), name='user-change-password'),
                path('group/', include(group_urls)),
                path('role/', include(role_urls)),
            ]
        ),
    ),
]
