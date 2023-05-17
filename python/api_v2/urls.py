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

from drf_yasg.openapi import Info, License
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny
from rest_framework.routers import re_path

SchemaView = get_schema_view(
    Info(
        title="ADCM API",
        default_version="v2",
        description="ArenaData Cluster Manager API",
        license=License(name="Apache 2.0 License"),
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = [
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", SchemaView.without_ui(cache_timeout=0), name="schema-json"),
    re_path(r"^swagger/$", SchemaView.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    re_path(r"^redoc/$", SchemaView.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
