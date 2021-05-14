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


from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.UserList.as_view(), name='user-list'),
    path('<name:username>/', include([
        path('', views.UserDetail.as_view(), name='user-details'),
        path('role/', views.ChangeUserRole.as_view(), name='change-user-role'),
        path('group/', views.AddUser2Group.as_view(), name='add-user-group'),
        path('password/', views.UserPasswd.as_view(), name='user-passwd'),
    ])),
]
