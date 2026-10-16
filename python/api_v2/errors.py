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

from cm.errors import AdcmEx
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _to_api_exception(exc: AdcmEx) -> APIException:
    api_exception = APIException(detail=exc.detail, code=exc.status_code)
    api_exception.status_code = exc.status_code
    return api_exception


def custom_drf_exception_handler(exc: Exception, context) -> Response | None:
    if isinstance(exc, ValidationError) and isinstance(exc.detail, dict):
        msg = os.linesep.join(_stringify_validation_error(detail=exc.detail))

        exc = AdcmEx(code="BAD_REQUEST", msg=msg)

    response = exception_handler(
        exc=_to_api_exception(exc) if isinstance(exc, AdcmEx) else exc,
        context=context,
    )

    if not isinstance(exc, AdcmEx) and response and 400 <= response.status_code <= 499:
        detail = response.status_code
        if hasattr(exc, "detail"):
            detail = exc.detail

        response.data = {
            "code": "API_ERROR",
            "level": "ERROR",
            "desc": detail,
        }

    return response


def _stringify_validation_error(detail, field_name=None) -> list[str]:
    if isinstance(detail, dict):
        messages = []
        for key, value in detail.items():
            messages.extend(_stringify_validation_error(detail=value, field_name=key))

        return messages

    if isinstance(detail, list):
        messages = []
        for item in detail:
            if isinstance(item, (dict | list)):
                messages.extend(_stringify_validation_error(detail=item, field_name=field_name))
            else:
                messages.append(f"{field_name} - {item}")

        return messages

    return [f"{field_name} - {detail}"]
