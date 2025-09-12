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

import re

from django.core.handlers.wsgi import WSGIRequest

AUDITED_HTTP_METHODS = frozenset(("POST", "DELETE", "PUT", "PATCH"))

URL_PATH_PATTERN = re.compile(r".*/api/v(?P<api_version>\d+)/(?P<target_path>.*?)/?$")


def get_client_ip(request: WSGIRequest) -> str | None:
    header_fields = ["HTTP_X_FORWARDED_FOR", "HTTP_X_FORWARDED_HOST", "HTTP_X_FORWARDED_SERVER", "REMOTE_ADDR"]
    host = None

    for field in header_fields:
        if field in request.META:
            host = request.META[field].split(",")[-1]
            break

    return host


def get_client_agent(request: WSGIRequest) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:255]
