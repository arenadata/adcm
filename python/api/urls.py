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

from api import views, user_views, docs, job_views


register_converter(views.NameConverter, 'name')
swagger_view = get_swagger_view(title='ArenaData Chapel API')
schema_view = get_schema_view(title='ArenaData Chapel API')


urlpatterns = [
    path('info/', views.ADCMInfo.as_view(), name='adcm-info'),
    path('token/', views.GetAuthToken.as_view(), name='token'),
    path('logout/', views.LogOut.as_view(), name='logout'),

    path('user/', include([
        path('', user_views.UserList.as_view(), name='user-list'),
        path('<name:username>/', include([
            path('', user_views.UserDetail.as_view(), name='user-details'),
            path('role/', user_views.ChangeUserRole.as_view(), name='change-user-role'),
            path('group/', user_views.AddUser2Group.as_view(), name='add-user-group'),
            path('password/', user_views.UserPasswd.as_view(), name='user-passwd'),
        ])),
    ])),

    path('group/', include([
        path('', user_views.GroupList.as_view(), name='group-list'),
        path('<name:name>/', include([
            path('', user_views.GroupDetail.as_view(), name='group-details'),
            path('role/', user_views.ChangeGroupRole.as_view(), name='change-group-role'),
        ])),
    ])),

    path('profile/', include([
        path('', user_views.ProfileList.as_view(), name='profile-list'),
        path('<name:username>/', include([
            path('', user_views.ProfileDetail.as_view(), name='profile-details'),
            path('password/', user_views.UserPasswd.as_view(), name='profile-passwd'),
        ])),
    ])),

    path('role/', include([
        path('', user_views.RoleList.as_view(), name='role-list'),
        path('<int:role_id>/', user_views.RoleDetail.as_view(), name='role-details'),
    ])),

    path('stats/', include([
        path('', views.Stats.as_view(), name='stats'),
        path('task/<int:task_id>/', views.TaskStats.as_view(), name='task-stats'),
        path('job/<int:job_id>/', views.JobStats.as_view(), name='job-stats'),
    ])),

    path('stack/', include('api.stack.urls')),
    path('cluster/', include('api.cluster.urls')),
    path('service/', include('api.service.urls')),
    path('component/', include('api.component.urls')),
    path('provider/', include('api.provider.urls')),
    path('host/', include('api.host.urls')),

    path('adcm/', include([
        path('', views.AdcmList.as_view(), name='adcm'),
        path('<int:adcm_id>/', include([
            path('', views.AdcmDetail.as_view(), name='adcm-details'),
            path('config/', include('api.config.urls'), {'object_type': 'adcm'}),
            path('action/', include('api.action.urls'), {'object_type': 'adcm'}),
        ])),
    ])),

    path('task/', include([
        path('', job_views.Task.as_view(), name='task'),
        path('<int:task_id>/', include([
            path('', job_views.TaskDetail.as_view(), name='task-details'),
            path('restart/', job_views.TaskReStart.as_view(), name='task-restart'),
            path('cancel/', job_views.TaskCancel.as_view(), name='task-cancel'),
        ])),
    ])),

    path('job/', include([
        path('', job_views.JobList.as_view(), name='job'),
        path('<int:job_id>/', include([
            path('', job_views.JobDetail.as_view(), name='job-details'),
            path('log/', include([
                path('', job_views.LogStorageListView.as_view(), name='log-list'),
                path('<int:log_id>/', include([
                    path('', job_views.LogStorageView.as_view(), name='log-storage'),
                    path('download/', job_views.download_log_file, name='download-log'),
                ])),
                path(
                    '<name:tag>/<name:level>/<name:log_type>/',
                    job_views.LogFile.as_view(),
                    name='log-file'
                ),
            ])),
        ])),
    ])),

    # path('docs/', include_docs_urls(title='ArenaData Chapel API')),
    path('swagger/', swagger_view),
    path('schema/', schema_view),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),

    path('docs/md/', docs.docs_md),
    path('docs/', docs.docs_html),

    path('', views.APIRoot.as_view()),
]
