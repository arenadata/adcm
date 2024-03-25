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

from cm.services.authorization import has_google_oauth, has_yandex_oauth
from cm.stack import NAME_REGEX
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.schemas.coreapi import AutoSchema
from rest_framework.views import APIView


class APIRoot(APIRootView):
    permission_classes = (AllowAny,)
    api_root_dict = {
        "adcm": "adcm-list",
        "audit": "audit:root",
        "cluster": "cluster",
        "provider": "provider",
        "host": "host",
        "service": "service",
        "component": "component",
        "group-config": "group-config-list",
        "config": "config-list",
        "config-log": "config-log-list",
        "job": "joblog-list",
        "stack": "stack",
        "stats": "stats",
        "task": "tasklog-list",
        "info": "adcm-info",
        "concern": "concern",
        "rbac": "rbac:root",
        "token": "token",
    }


class NameConverter:
    regex = NAME_REGEX

    @staticmethod
    def to_python(value):
        return value

    @staticmethod
    def to_url(value):
        return value


class ADCMInfo(APIView):
    permission_classes = (AllowAny,)
    schema = AutoSchema()

    @staticmethod
    def get(request):  # noqa: ARG004
        return Response(
            {
                "adcm_version": settings.ADCM_VERSION,
                "google_oauth": has_google_oauth(),
                "yandex_oauth": has_yandex_oauth(),
            },
        )
