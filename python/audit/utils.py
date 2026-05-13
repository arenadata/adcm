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

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum, auto
from json import JSONDecodeError
import re
import json

from cm.models import ADCM, ConfigLog
from core.types import CurrentADCMVersion
from django.conf import settings
from django.db.models import F, Subquery
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.urls import resolve
from django.utils import timezone
from rbac.models import User as RBACUser

from audit.cef_logger import cef_logger
from audit.models import AuditSession, AuditSessionLoginResult, AuditUser

AUDITED_HTTP_METHODS = frozenset(("POST", "DELETE", "PUT", "PATCH"))

URL_PATH_PATTERN = re.compile(r".*/api/v(?P<api_version>\d+)/(?P<target_path>.*?)/?$")


class UserNotFoundError(Exception):
    ...


class LogInResult(Enum):
    SUCCESS = auto()
    FAIL = auto()


class BlockStatus(Enum):
    ACTIVE = auto()
    TEMPORARILY_BLOCKED = auto()


@dataclass(slots=True, frozen=True)
class LoginSettings:
    attempts: int
    block_duration: timedelta


def get_client_ip(request: HttpRequest) -> str | None:
    header_fields = ["HTTP_X_FORWARDED_FOR", "HTTP_X_FORWARDED_HOST", "HTTP_X_FORWARDED_SERVER", "REMOTE_ADDR"]
    host = None

    for field in header_fields:
        if field in request.META:
            host = request.META[field].split(",")[-1]
            break

    return host


def get_client_agent(request: HttpRequest) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:255]


def build_forbidden_response() -> HttpResponseForbidden:
    return HttpResponseForbidden(
        content=json.dumps(
            {
                "code": "USER_BLOCK_ERROR",
                "level": "error",
                "desc": "Account locked: Please try again later or contact to ADCM Administrator",
            },
        ).encode(encoding=settings.ENCODING_UTF_8),
    )


def retrieve_login_settings() -> LoginSettings | None:
    config = (
        ConfigLog.objects.filter(id__in=Subquery(ADCM.objects.values("config__current")))
        .values_list("config", flat=True)
        .get()
    )

    if config.get("auth_policy"):
        login_attempt_limit = config["auth_policy"]["login_attempt_limit"]
        block_time_minutes = config["auth_policy"]["block_time"]

        return LoginSettings(attempts=login_attempt_limit, block_duration=timedelta(minutes=block_time_minutes))

    return None


def retrieve_request_username(request: HttpRequest) -> str:
    try:
        username = json.loads(request.body.decode(settings.ENCODING_UTF_8)).get("username")
    except JSONDecodeError:
        username = ""

    return request.POST.get("username") or username or request.user.username


def detect_login_result(request: HttpRequest, username: str) -> tuple[RBACUser, LogInResult]:
    user = request.user

    if user is not None and user.is_authenticated:
        return user.user, LogInResult.SUCCESS

    try:
        return RBACUser.objects.get(username=username), LogInResult.FAIL

    except RBACUser.DoesNotExist as e:
        raise UserNotFoundError from e


def detect_user_block_status(user: RBACUser, login_settings: LoginSettings) -> BlockStatus:
    if user.blocked_at:
        user_blocked_till = user.blocked_at + login_settings.block_duration
        if not user_blocked_till < timezone.now():
            return BlockStatus.TEMPORARILY_BLOCKED

    return BlockStatus.ACTIVE


def detect_audit_result(login_result: LogInResult, block_status: BlockStatus) -> AuditSessionLoginResult:
    match login_result:
        case LogInResult.FAIL:
            return AuditSessionLoginResult.WRONG_PASSWORD

        case LogInResult.SUCCESS:
            match block_status:
                case BlockStatus.ACTIVE:
                    return AuditSessionLoginResult.SUCCESS

                case BlockStatus.TEMPORARILY_BLOCKED:
                    return AuditSessionLoginResult.LOG_IN_TO_A_BLOCKED_ACCOUNT


def detect_response(login_result: LogInResult, block_status: BlockStatus, response: HttpResponse) -> HttpResponse:
    if block_status == BlockStatus.TEMPORARILY_BLOCKED:
        if login_result == LogInResult.FAIL:
            return response

        return build_forbidden_response()

    return response


def update_login_attempts_get_block_status(
    user: RBACUser, login_result: LogInResult, login_settings: LoginSettings
) -> BlockStatus:
    block_status = detect_user_block_status(user=user, login_settings=login_settings)

    match login_result:
        case LogInResult.SUCCESS if block_status == BlockStatus.ACTIVE:
            user.failed_login_attempts = 0
            user.blocked_at = None
            user.save(update_fields=["failed_login_attempts", "blocked_at"])

        case LogInResult.FAIL:
            user.failed_login_attempts = F("failed_login_attempts") + 1
            user.last_failed_login_at = timezone.now()
            user.save(update_fields=["failed_login_attempts", "last_failed_login_at"])

    user.refresh_from_db(fields=["failed_login_attempts"])
    if user.failed_login_attempts >= login_settings.attempts:
        user.blocked_at = timezone.now()
        user.save(update_fields=["blocked_at"])

        return BlockStatus.TEMPORARILY_BLOCKED

    return BlockStatus.ACTIVE


def create_audit_records(
    username: str, result: AuditSessionLoginResult, adcm_version: CurrentADCMVersion, request: HttpRequest
) -> None:
    audit_user = AuditUser.objects.filter(username=username).order_by("-pk").first()

    audit_session = AuditSession.objects.create(
        user=audit_user,
        login_result=result,
        login_details={"username": username[: settings.USERNAME_MAX_LENGTH]},
        address=get_client_ip(request=request),
        agent=get_client_agent(request=request),
    )
    cef_logger(audit_instance=audit_session, signature_id=resolve(request.path).route, adcm_version=adcm_version)
