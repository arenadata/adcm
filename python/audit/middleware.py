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

from typing import Final

from core.types import CurrentADCMVersion
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from typing_extensions import Self

from audit.models import AuditSessionLoginResult
from audit.utils import (
    BlockStatus,
    LogInResult,
    UserNotFoundError,
    build_forbidden_response,
    create_audit_records,
    detect_audit_result,
    detect_login_result,
    detect_response,
    retrieve_login_settings,
    retrieve_request_username,
    update_login_attempts_get_block_status,
)


class LoginMiddleware:
    target_url_paths: Final = {
        "/auth/login/",
        "/api/v2/login/",
        "/api/v2/token/",
    }

    def __init__(self: Self, get_response):
        self.get_response = get_response

    def __call__(self: Self, request: HttpRequest) -> HttpResponse:
        if not self.is_login_request(request=request):
            return self.get_response(request)

        username = retrieve_request_username(request=request)
        adcm_version = request.container.get(CurrentADCMVersion)

        response = self.get_response(request)

        return audit_request_return_response(
            username=username, adcm_version=adcm_version, request=request, response=response
        )

    def is_login_request(self: Self, request: HttpRequest) -> bool:
        return request.method == "POST" and request.path in self.target_url_paths


def audit_request_return_response(
    username: str,
    adcm_version: CurrentADCMVersion,
    request: HttpRequest,
    response: HttpResponse,
) -> HttpResponse:
    try:
        user, login_result = detect_login_result(request=request, username=username)
    except UserNotFoundError:
        create_audit_records(
            username=username,
            result=AuditSessionLoginResult.USER_NOT_FOUND,
            adcm_version=adcm_version,
            request=request,
        )
        return response

    block_status = BlockStatus.ACTIVE
    if not user.is_active:
        audit_result = AuditSessionLoginResult.ACCOUNT_DISABLED
        response = build_forbidden_response()
    else:
        if login_settings := retrieve_login_settings():
            block_status = update_login_attempts_get_block_status(
                user=user, login_result=login_result, login_settings=login_settings
            )
        else:
            block_status = BlockStatus.ACTIVE
        audit_result = detect_audit_result(login_result=login_result, block_status=block_status)

    create_audit_records(
        username=user.username,
        result=audit_result,
        adcm_version=adcm_version,
        request=request,
    )

    if login_result == LogInResult.SUCCESS and audit_result != AuditSessionLoginResult.SUCCESS:
        logout(request=request)

    return detect_response(login_result=login_result, block_status=block_status, response=response)
