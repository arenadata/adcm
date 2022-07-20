from functools import wraps

from audit.models import (
    AUDIT_OPERATION_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditObject,
)
from cm.errors import AdcmEx
from django.views.generic.base import View
from rest_framework.status import is_success


def audit(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        error = None

        try:
            resp = func(*args, **kwargs)
            status_code = resp.status_code
        except AdcmEx as exc:
            error = exc
            resp = None
            status_code = exc.status_code

        view: View = args[0]
        audit_operation = AUDIT_OPERATION_MAP[view.__class__.__name__][view.request.method]
        object_changes = {}

        if is_success(status_code):
            operation_result = AuditLogOperationResult.Success
            if resp.data:
                audit_object = AuditObject.objects.create(
                    object_id=resp.data.serializer.instance.id,
                    object_name=resp.data.serializer.instance.name,
                    object_type=audit_operation.object_type,
                )
            else:
                audit_object = None
        else:
            operation_result = AuditLogOperationResult.Failed
            audit_object = None

        AuditLog.objects.create(
            audit_object=audit_object,
            operation_name=audit_operation.name,
            operation_type=audit_operation.operation_type,
            operation_result=operation_result,
            user=view.request.user,
            object_changes=object_changes,
        )

        if error:
            raise error

        return resp

    return wrapped
