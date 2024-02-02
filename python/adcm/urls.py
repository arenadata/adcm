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

from django.conf.urls import include
from django.urls import path

from adcm.views import ADCMVersions

urlpatterns = [
    path("social/", include("social_django.urls", namespace="social")),
    path("auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/v1/", include(("api.urls", "api"), namespace="v1")),
    path("api/v2/", include(("api_v2.urls", "api_v2"), namespace="v2")),
    path("api/ui/", include("api_ui.urls")),
    path("versions/", ADCMVersions.as_view(), name="versions"),
]

handler500 = "adcm.views.server_error"
handler404 = "adcm.views.page_not_found"
