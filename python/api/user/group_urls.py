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
    path('', views.GroupList.as_view(), name='group-list'),
    path('<name:name>/', include([
        path('', views.GroupDetail.as_view(), name='group-details'),
        path('role/', views.ChangeGroupRole.as_view(), name='change-group-role'),
    ])),
]
