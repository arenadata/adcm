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

from api_v2.views import APIRoot
from django.urls import include, path

urlpatterns = [
    path("", APIRoot.as_view(), name="api-root-v2"),
    path("clusters/", include("api_v2.cluster.urls")),
    path("bundles/", include("api_v2.bundle.urls")),
    path("prototypes/", include("api_v2.prototype.urls")),
    path("hosts/", include("api_v2.host.urls")),
    path("hostproviders/", include("api_v2.hostprovider.urls")),
    path("audit/", include(("api_v2.audit.urls", "audit"))),
    path("jobs/", include("api_v2.job.urls")),
]
