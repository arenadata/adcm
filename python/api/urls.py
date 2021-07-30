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

from django.urls import path, include, register_converter

from rest_framework_swagger.views import get_swagger_view
from rest_framework.schemas import get_schema_view

from api import views, docs
from api.search.views import Search


register_converter(views.NameConverter, 'name')
swagger_view = get_swagger_view(title='ArenaData Chapel API')
schema_view = get_schema_view(title='ArenaData Chapel API')


urlpatterns = [
    path('info/', views.ADCMInfo.as_view(), name='adcm-info'),
    path('stats/', include('api.stats.urls')),
    path('token/', views.GetAuthToken.as_view(), name='token'),
    path('logout/', views.LogOut.as_view(), name='logout'),
    path('user/', include('api.user.urls')),
    path('group/', include('api.user.group_urls')),
    path('role/', include('api.user.role_urls')),
    path('profile/', include('api.user.profile_urls')),
    path('stack/', include('api.stack.urls')),
    path('cluster/', include('api.cluster.urls')),
    path('service/', include('api.service.urls')),
    path('component/', include('api.component.urls')),
    path('provider/', include('api.provider.urls')),
    path('host/', include('api.host.urls')),
    path('adcm/', include('api.adcm.urls')),
    path('task/', include('api.job.task_urls')),
    path('job/', include('api.job.urls')),
    # path('docs/', include_docs_urls(title='ArenaData Chapel API')),
    path('search/', Search.as_view()),
    path('swagger/', swagger_view),
    path('schema/', schema_view),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('docs/md/', docs.docs_md),
    path('docs/', docs.docs_html),
    path('', views.APIRoot.as_view()),
]
