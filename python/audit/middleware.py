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
from cm.logger import log
from rbac.models import User


def create_audit_session(user, result, details):
    AuditSession.objects.create(user=user, login_result=result, login_details=details)


class AuditLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        log.debug(f"before response {request.user}")
        response = self.get_response(request)
        if request.path == '/api/v1/rbac/token/':
            if request.user.is_authenticated:
                create_audit_session(request.user, AuditSessionLoginResult.Success, None)
            else:
                log.debug(f"wow {request.user}")
                body = json.loads(request.body.decode('utf-8'))
                username = body['username']
                try:
                    user = User.objects.get(username=username)

                    if not user.is_active:
                        create_audit_session(
                            None, AuditSessionLoginResult.AccountDisabled, {"username": username}
                        )
                    else:
                        create_audit_session(
                            None, AuditSessionLoginResult.WrongPassword, {"username": username}
                        )
                except User.DoesNotExist:
                    create_audit_session(
                        None, AuditSessionLoginResult.UserNotFound, {"username": username}
                    )
                    return response

        return response
