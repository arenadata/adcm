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

from django.urls import path
from rest_framework.routers import SimpleRouter

from api.job.views import JobViewSet, LogStorageViewSet

router = SimpleRouter()
router.register("", JobViewSet, basename="joblog")

urlpatterns = [
    *router.urls,
    path("<int:job_pk>/log/", LogStorageViewSet.as_view({"get": "list"}), name="logstorage-list"),
    path(
        "<int:job_pk>/log/<int:log_pk>/",
        LogStorageViewSet.as_view({"get": "retrieve"}),
        name="logstorage-detail",
    ),
    path(
        "<int:job_pk>/log/<int:log_pk>/download/",
        LogStorageViewSet.as_view({"get": "download"}),
        name="logstorage-download",
    ),
]
