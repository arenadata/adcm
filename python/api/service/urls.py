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
    path(
        'service/',
        views.ServiceListView.as_view(),
        name='service'
    ),
    path(
        'service/<int:service_id>/',
        views.ServiceDetailView.as_view(),
        name='service-details'
    ),
    path(
        'service/<int:service_id>/action/',
        views.ServiceActionListView.as_view(),
        name='service-action'
    ),
    path(
        'service/<int:service_id>/action/<int:action_id>/',
        views.ServiceActionView.as_view(),
        name='service-action-details'
    ),
    path(
        'service/<int:service_id>/action/<int:action_id>/run/',
        views.ServiceTask.as_view(),
        name='service-action-run'
    ),
    path(
        'service/<int:service_id>/component/',
        views.ServiceComponentListView.as_view(),
        name='service-component'
    ),
    path(
        'service/<int:service_id>/component/<int:component_id>/',
        views.ServiceComponentDetailView.as_view(),
        name='service-component-details'
    ),
    path(
        'service/<int:service_id>/import/',
        views.ServiceImportView.as_view(),
        name='service-import'
    ),
    path(
        'service/<int:service_id>/bind/',
        views.ServiceBindView.as_view(),
        name='service-bind'
    ),
    path(
        'service/<int:service_id>/bind/<int:bind_id>/',
        views.ServiceBindDetailView.as_view(),
        name='service-bind-details'
    ),
    path(
        'service/<int:service_id>/config/',
        include('api.config.urls'),
        {'object_type': 'service'}
    ),
]
