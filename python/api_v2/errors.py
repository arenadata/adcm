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
        msg = ""
        for field_name, error in exc.detail.items():
            if isinstance(error, list):
                if isinstance(error[0], dict):
                    for err_type, err in error[0].items():
                        msg = f"{msg}{err_type} - {err[0]};"
                else:
                    msg = f"{msg}{field_name} - {error[0]};"
            else:
                for err_type, err in error.items():
                    msg = f"{msg}{err_type} - {err[0]};"

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
