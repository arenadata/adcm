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

from json.decoder import JSONDecodeError
import json

from cm.models import ADCM, ConfigLog
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.models import AnonymousUser, User
from django.http.response import HttpResponseForbidden
from django.urls import resolve
from django.utils import timezone
from rbac.models import User as RBACUser

from audit.cef_logger import cef_logger
from audit.models import AuditSession, AuditSessionLoginResult, AuditUser
from audit.utils import get_client_ip


class LoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _audit(
        request_path: str,
        request_host: str | None,
        user: User | AnonymousUser | None = None,
        username: str = None,
    ) -> tuple[User | None, AuditSessionLoginResult]:
        if user is not None and user.is_authenticated:
            result = AuditSessionLoginResult.SUCCESS
            details = {"username": user.username}
        else:
            details = {"username": username[: settings.USERNAME_MAX_LENGTH]}
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    result = AuditSessionLoginResult.ACCOUNT_DISABLED
                else:
                    result = AuditSessionLoginResult.WRONG_PASSWORD

            except User.DoesNotExist:
                result = AuditSessionLoginResult.USER_NOT_FOUND
                user = None

        audit_user = None
        if user is not None:
            audit_user = AuditUser.objects.filter(username=user.username).order_by("-pk").first()

        audit_session = AuditSession.objects.create(
            user=audit_user, login_result=result, login_details=details, address=request_host
        )
        cef_logger(audit_instance=audit_session, signature_id=resolve(request_path).route)

        return user, result

    def _process_login_attempts(
        self,
        user: RBACUser | User,
        result: AuditSessionLoginResult,
    ) -> HttpResponseForbidden | None:
        user = user if isinstance(user, RBACUser) else user.user
        config_log = None
        login_attempt_limit = None
        block_time_minutes = None

        adcm = ADCM.objects.first()
        if adcm:
            config_log = ConfigLog.objects.filter(obj_ref=adcm.config).last()

        if config_log and isinstance(config_log.config, dict) and config_log.config.get("auth_policy"):
            login_attempt_limit = config_log.config["auth_policy"]["login_attempt_limit"]
            block_time_minutes = config_log.config["auth_policy"]["block_time"]

        if not all((login_attempt_limit, block_time_minutes)):
            return None

        if result == AuditSessionLoginResult.SUCCESS:
            if user.blocked_at:
                user_blocked_till = user.blocked_at + timezone.timedelta(minutes=block_time_minutes)
                user_block_period_past = user_blocked_till < timezone.now()
                if not user_block_period_past:
                    return self._build_forbidden_response()

            user.failed_login_attempts = 0
            user.blocked_at = None
            user.save(update_fields=["failed_login_attempts", "blocked_at"])

            return None
        else:
            if user.blocked_at:
                user_blocked_till = user.blocked_at + timezone.timedelta(minutes=block_time_minutes)
                user_block_period_past = user_blocked_till < timezone.now()
                if not user_block_period_past:
                    return self._build_forbidden_response()
                else:
                    user.failed_login_attempts = 1
                    user.blocked_at = None
            else:
                if (
                    user.last_failed_login_at
                    and (user.last_failed_login_at + timezone.timedelta(minutes=block_time_minutes)) < timezone.now()
                    and user.failed_login_attempts == 0
                ):
                    user.failed_login_attempts = 1
                else:
                    user.failed_login_attempts += 1

                user.last_failed_login_at = timezone.now()

            if user.failed_login_attempts >= login_attempt_limit:
                user.blocked_at = timezone.now()
                user.save(update_fields=["failed_login_attempts", "blocked_at", "last_failed_login_at"])

                return self._build_forbidden_response()
            else:
                user.save(update_fields=["failed_login_attempts", "blocked_at", "last_failed_login_at"])

                return None

    def _build_forbidden_response(self):
        return HttpResponseForbidden(
            content=json.dumps(
                {
                    "code": "USER_BLOCK_ERROR",
                    "level": "error",
                    "desc": "Account locked: Please try again later or contact to ADCM Administrator",
                },
            ).encode(encoding=settings.ENCODING_UTF_8),
        )

    def __call__(self, request):
        if not (
            request.method == "POST"
            and request.path
            in {
                "/api/v1/rbac/token/",
                "/api/v1/token/",
                "/auth/login/",
                "/api/v2/login/",
                "/api/v2/token/",
            }
        ):
            return self.get_response(request)

        try:
            username = json.loads(request.body.decode(settings.ENCODING_UTF_8)).get("username")
        except JSONDecodeError:
            username = ""

        response = self.get_response(request)

        username = request.POST.get("username") or username or request.user.username
        user, result = self._audit(
            request_path=request.path,
            request_host=get_client_ip(request=request),
            user=request.user,
            username=username,
        )

        if user:
            if not user.is_active:
                return self._build_forbidden_response()

            if login_attempts_response := self._process_login_attempts(user=user, result=result):
                logout(request=request)
                return login_attempts_response

        return response
