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

from rest_framework.urls import path

from api.config_host_group.views import (
    CHGConfigLogViewSet,
    CHGConfigViewSet,
    CHGHostCandidateViewSet,
    CHGHostViewSet,
    CHGViewSet,
)

urlpatterns = [
    path(r"", CHGViewSet.as_view({"get": "list", "post": "create"}), name="group-config-list"),
    path(
        r"<int:pk>/",
        CHGViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="group-config-detail",
    ),
    path(
        r"<int:parent_lookup_group_config>/host/",
        CHGHostViewSet.as_view({"get": "list", "post": "create"}),
        name="group-config-host-list",
    ),
    path(
        r"<int:parent_lookup_group_config>/host/<int:host_id>/",
        CHGHostViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="group-config-host-detail",
    ),
    path(
        r"<int:parent_lookup_group_config>/host-candidate/",
        CHGHostCandidateViewSet.as_view({"get": "list"}),
        name="group-config-host-candidate-list",
    ),
    path(
        r"<int:parent_lookup_group_config>/host-candidate/<int:host_id>/",
        CHGHostCandidateViewSet.as_view({"get": "retrieve"}),
        name="group-config-host-candidate-detail",
    ),
    path(
        r"<int:parent_lookup_group_config>/config/<int:pk>/",
        CHGConfigViewSet.as_view({"get": "retrieve"}),
        name="group-config-config-detail",
    ),
    path(
        r"<int:parent_lookup_obj_ref__group_config>/config/<int:parent_lookup_obj_ref>/config-log/",
        CHGConfigLogViewSet.as_view({"get": "list", "post": "create"}),
        name="group-config-config-log-list",
    ),
    path(
        r"<int:parent_lookup_obj_ref__group_config>/config/<int:parent_lookup_obj_ref>/config-log/<int:pk>/",
        CHGConfigLogViewSet.as_view({"get": "retrieve"}),
        name="group-config-config-log-detail",
    ),
]
