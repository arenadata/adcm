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

from cm.stack import NAME_REGEX
from django.conf import settings
from rest_framework import permissions, routers
from rest_framework.response import Response
from rest_framework.views import APIView

from adcm.utils import has_google_oauth, has_yandex_oauth


class APIRoot(routers.APIRootView):
    permission_classes = (permissions.AllowAny,)
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
    permission_classes = (permissions.AllowAny,)

    @staticmethod
    def get(request):  # pylint: disable=unused-argument
        return Response(
            {
                "adcm_version": settings.ADCM_VERSION,
                "google_oauth": has_google_oauth(),
                "yandex_oauth": has_yandex_oauth(),
            },
        )
