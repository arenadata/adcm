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

from django.urls import include, path, register_converter
from rbac.endpoints import token
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import (
    BrowsableAPIRenderer,
    CoreAPIOpenAPIRenderer,
    CoreJSONRenderer,
)
from rest_framework.schemas.coreapi import SchemaGenerator
from rest_framework.schemas.views import SchemaView

from api import docs, views

register_converter(views.NameConverter, "name")
generator = SchemaGenerator(title="ArenaData Chapel API", patterns=[path("api/v1/", include("api.urls"))])
authentication_classes = (SessionAuthentication, TokenAuthentication)
permission_classes = (IsAuthenticated,)
renderer_classes = (BrowsableAPIRenderer, CoreAPIOpenAPIRenderer, CoreJSONRenderer)


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
    path(
        "schema/",
        SchemaView.as_view(
            renderer_classes=renderer_classes,
            schema_generator=generator,
            public=False,
            authentication_classes=authentication_classes,
            permission_classes=permission_classes,
        ),
    ),
    path("docs/md/", docs.docs_md),
    path("docs/", docs.docs_html),
    path("rbac/", include(("rbac.urls", "rbac"))),
    path("token/", token.GetAuthToken.as_view(), name="token"),
]
