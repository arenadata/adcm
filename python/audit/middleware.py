import json

from audit.models import AuditSession, AuditSessionLoginResult
from rbac.models import User


def create_audit_session(user, result, details):
    AuditSession.objects.create(user=user, login_result=result, login_details=details)


class AuditLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path == '/api/v1/rbac/token/':
            if request.user.is_authenticated:
                create_audit_session(request.user, AuditSessionLoginResult.Success, None)
            else:
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
