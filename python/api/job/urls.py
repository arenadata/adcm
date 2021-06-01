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

# fmt: off
urlpatterns = [
    path('', views.JobList.as_view(), name='job'),
    path('<int:job_id>/', include([
        path('', views.JobDetail.as_view(), name='job-details'),
        path('log/', include([
            path('', views.LogStorageListView.as_view(), name='log-list'),
            path('<int:log_id>/', include([
                path('', views.LogStorageView.as_view(), name='log-storage'),
                path('download/', views.download_log_file, name='download-log'),
            ])),
            path(
                '<name:tag>/<name:level>/<name:log_type>/',
                views.LogFile.as_view(),
                name='log-file'
            ),
        ])),
    ])),
]
# fmt: on
