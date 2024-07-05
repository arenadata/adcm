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

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerSplitView,
)

from api_v2.login.views import LoginView
from api_v2.logout.views import LogoutView
from api_v2.profile.views import ProfileView
from api_v2.token.views import TokenView
from api_v2.views import APIRoot

urlpatterns = [
    path("", APIRoot.as_view(), name="api-root-v2"),
    path("rbac/", include(("api_v2.rbac.urls", "rbac"))),
    path("clusters/", include("api_v2.cluster.urls")),
    path("bundles/", include("api_v2.bundle.urls")),
    path("prototypes/", include("api_v2.prototype.urls")),
    path("hosts/", include("api_v2.host.urls")),
    path("hostproviders/", include("api_v2.hostprovider.urls")),
    path("audit/", include(("api_v2.audit.urls", "audit"))),
    path("jobs/", include("api_v2.job.urls")),
    path("tasks/", include("api_v2.task.urls")),
    path("adcm/", include("api_v2.adcm.urls")),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view({"get": "retrieve", "patch": "partial_update"}), name="profile"),
    path("token/", TokenView.as_view(), name="token"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/swagger-ui/", SpectacularSwaggerSplitView.as_view(url_name="schema"), name="swagger-ui"),
    path("schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
