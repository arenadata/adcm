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

from api.service.views import (
    ServiceBindDetailView,
    ServiceBindView,
    ServiceDetailView,
    ServiceImportView,
    ServiceListView,
    ServiceMaintenanceModeView,
    StatusList,
)
from django.urls import include, path

urlpatterns = [
    path("", ServiceListView.as_view(), name="service"),
    path(
        "<int:service_id>/",
        include(
            [
                path("", ServiceDetailView.as_view(), name="service-details"),
                path(
                    "maintenance-mode/",
                    ServiceMaintenanceModeView.as_view(),
                    name="service-maintenance-mode",
                ),
                path("component/", include("api.component.urls")),
                path("import/", ServiceImportView.as_view(), name="service-import"),
                path(
                    "bind/",
                    include(
                        [
                            path("", ServiceBindView.as_view(), name="service-bind"),
                            path(
                                "<int:bind_id>/",
                                ServiceBindDetailView.as_view(),
                                name="service-bind-details",
                            ),
                        ]
                    ),
                ),
                path("config/", include("api.config.urls"), {"object_type": "service"}),
                path("action/", include("api.action.urls"), {"object_type": "service"}),
                path("status/", StatusList.as_view(), name="service-status"),
            ]
        ),
    ),
]
