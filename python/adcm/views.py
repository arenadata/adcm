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

from django.http.request import HttpRequest
from django.http.response import JsonResponse
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR


def server_error(request: HttpRequest, *args, **kwargs) -> JsonResponse:  # pylint: disable=unused-argument
    data = {
        "code": HTTP_500_INTERNAL_SERVER_ERROR,
        "level": "error",
        "desc": "Server Error (500)",
    }
    return JsonResponse(data=data, status=HTTP_500_INTERNAL_SERVER_ERROR)


def page_not_found(request: HttpRequest, *args, **kwargs) -> JsonResponse:  # pylint: disable=unused-argument
    data = {
        "code": HTTP_404_NOT_FOUND,
        "level": "error",
        "desc": "URL not found (404)",
    }
    return JsonResponse(data=data, status=HTTP_404_NOT_FOUND)
