from functools import wraps

from adwp_base.errors import AdwpEx
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
        except (AdcmEx, AdwpEx) as exc:
            error = exc
            resp = None
            status_code = exc.status_code

        view: View = args[0]
        audit_operation = AUDIT_OPERATION_MAP[view.__class__.__name__][view.request.method]
        object_changes = {}

        if is_success(status_code):
            operation_result = AuditLogOperationResult.Success
            if resp.data:
                if resp.data.get("serializer"):
                    if hasattr(resp.data.serializer.instance, "name"):
                        object_name = resp.data.serializer.instance.name
                    elif hasattr(resp.data.serializer.instance, "fqdn"):
                        object_name = resp.data.serializer.instance.fqdn
                    else:
                        object_name = str(resp.data.serializer.instance)

                    object_id = resp.data.serializer.instance.id
                else:
                    # For token there is no actually audit object
                    object_name = audit_operation.object_type
                    object_id = args[1].user.pk

                audit_object = AuditObject.objects.create(
                    object_id=object_id,
                    object_name=object_name,
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


def mark_deleted_audit_object(instance):
    audit_objs = []
    for audit_obj in AuditObject.objects.filter(object_id=instance.pk):
        audit_obj.is_deleted = True
        audit_objs.append(audit_obj)

    AuditObject.objects.bulk_update(objs=audit_objs, fields=["is_deleted"])
