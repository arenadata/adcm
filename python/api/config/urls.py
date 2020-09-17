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

from . import views


urlpatterns = [
    path(
        '',
        views.ConfigView.as_view(),
        name='config'
    ),
    path(
        'history/',
        views.ConfigHistoryView.as_view(),
        name='config-history'
    ),
    path(
        'history/<int:version>/',
        views.ConfigVersionView.as_view(),
        name='config-history-version'
    ),
    path(
        'history/<int:version>/restore/',
        views.ConfigHistoryRestoreView.as_view(),
        name='config-history-version-restore'
    ),
    path(
        'previous/',
        views.ConfigVersionView.as_view(),
        {'version': 'previous'},
        name='config-previous'
    ),
    path(
        'current/',
        views.ConfigVersionView.as_view(),
        {'version': 'current'},
        name='config-current'
    )
]
