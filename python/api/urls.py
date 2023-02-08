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

from api import docs, views
from django.urls import include, path, register_converter
from rbac.endpoints import token
from rest_framework.schemas import get_schema_view

register_converter(views.NameConverter, "name")
schema_view = get_schema_view(title="ArenaData Chapel API", patterns=[path("api/v1/", include("api.urls"))])

urlpatterns = [
    path("", views.APIRoot.as_view()),
    path("info/", views.ADCMInfo.as_view(), name="adcm-info"),
    path("stats/", include("api.stats.urls")),
    path("stack/", include("api.stack.urls")),
    path("cluster/", include("api.cluster.urls")),
    path("service/", include("api.service.urls")),
    path("component/", include("api.component.urls")),
    path("provider/", include("api.provider.urls")),
    path("host/", include("api.host.urls")),
    path("adcm/", include("api.adcm.urls")),
    path("group-config/", include("api.group_config.urls")),
    path("config/", include("api.object_config.urls")),
    path("config-log/", include("api.config_log.urls")),
    path("task/", include("api.job.task_urls")),
    path("job/", include("api.job.urls")),
    path("concern/", include("api.concern.urls")),
    path("audit/", include(("audit.urls", "audit"))),
    path("schema/", schema_view),
    path("auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("docs/md/", docs.docs_md),
    path("docs/", docs.docs_html),
    path("rbac/", include(("rbac.urls", "rbac"))),
    path("token/", token.GetAuthToken.as_view(), name="token"),
]
