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

from api.action.views import ActionDetail, ActionList, RunTask

urlpatterns = [
    path("", ActionList.as_view(), name="object-action"),
    path("<int:action_id>/", ActionDetail.as_view(), name="object-action-details"),
    path("<int:action_id>/run/", RunTask.as_view(), name="run-task"),
]
