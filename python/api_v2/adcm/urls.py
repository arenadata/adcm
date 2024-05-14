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

from api_v2.action.views import AdcmActionViewSet
from api_v2.adcm.views import ADCMConfigView, ADCMViewSet

urlpatterns = [
    path("", ADCMViewSet.as_view({"get": "retrieve"}), name="adcm-detail"),
    path("configs/", ADCMConfigView.as_view({"get": "list", "post": "create"}), name="adcm-config-list"),
    path("configs/<int:pk>/", ADCMConfigView.as_view({"get": "retrieve"}), name="adcm-config-detail"),
    path("config-schema/", ADCMConfigView.as_view({"get": "config_schema"}), name="adcm-config-schema"),
    path("actions/", AdcmActionViewSet.as_view({"get": "list"}), name="adcm-action-list"),
    path("actions/<int:pk>/", AdcmActionViewSet.as_view({"get": "retrieve"}), name="adcm-action-detail"),
    path("actions/<int:pk>/run/", AdcmActionViewSet.as_view({"post": "run"}), name="adcm-action-run"),
]
