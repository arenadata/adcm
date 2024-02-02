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
import os

from django.conf import settings
from django.http.request import HttpRequest
from django.http.response import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from rest_framework.views import APIView


def server_error(request: HttpRequest, *args, **kwargs) -> JsonResponse:  # noqa: ARG001
    data = {
        "code": HTTP_500_INTERNAL_SERVER_ERROR,
        "level": "error",
        "desc": "Server Error (500)",
    }
    return JsonResponse(data=data, status=HTTP_500_INTERNAL_SERVER_ERROR)


def page_not_found(request: HttpRequest, *args, **kwargs) -> JsonResponse:  # noqa: ARG001
    data = {
        "code": HTTP_404_NOT_FOUND,
        "level": "error",
        "desc": "URL not found (404)",
    }
    return JsonResponse(data=data, status=HTTP_404_NOT_FOUND)


class ADCMVersions(APIView):
    permission_classes = (AllowAny,)

    @staticmethod
    def get(request, *args, **kwargs) -> Response:  # noqa: ARG004
        return Response(
            data={"adcm": {"version": os.getenv("ADCM_VERSION", settings.ADCM_VERSION)}}, status=HTTP_200_OK
        )
