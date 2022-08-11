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

from django.contrib.auth.models import AnonymousUser, User

from audit.models import AuditSession, AuditSessionLoginResult


class AuditLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _audit(user: User | AnonymousUser = None, username: str = None):
        """Authentication audit"""
        if user.is_authenticated:
            result = AuditSessionLoginResult.Success
            details = {}
        else:
            details = {"username": username}
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    result = AuditSessionLoginResult.AccountDisabled
                else:
                    result = AuditSessionLoginResult.WrongPassword
            except User.DoesNotExist:
                result = AuditSessionLoginResult.UserNotFound
                user = None

        AuditSession.objects.create(user=user, login_result=result, login_details=details)

    def __call__(self, request):
        response = self.get_response(request)

        if request.method == "POST" and request.path in [
            "/api/v1/rbac/token/",
            "/api/v1/token/",
            "/api/v1/auth/login/",
        ]:
            username = request.POST.get("username") or request.user.username
            self._audit(user=request.user, username=username)

        return response
