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

import json

from audit.models import AuditSession, AuditSessionLoginResult
from rbac.models import User


class AuditLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path == '/api/v1/rbac/token/':
            return self.get_response(request)

        body = json.loads(request.body.decode('utf-8'))
        username = body['username']
        response = self.get_response(request)

        if request.user.is_authenticated:
            audit_user = request.user
            result = AuditSessionLoginResult.Success
            details = None
        else:
            audit_user = None
            details = {"username": username}
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    result = AuditSessionLoginResult.AccountDisabled
                else:
                    result = AuditSessionLoginResult.WrongPassword
            except User.DoesNotExist:
                result = AuditSessionLoginResult.UserNotFound

        AuditSession.objects.create(user=audit_user, login_result=result, login_details=details)

        return response
