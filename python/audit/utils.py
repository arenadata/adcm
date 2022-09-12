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
# pylint: disable=too-many-lines

from functools import wraps

from adwp_base.errors import AdwpEx
from django.contrib.auth.models import User as DjangoUser
from django.db.models import Model
from django.http.response import Http404
from django.urls import resolve
from django.views.generic.base import View
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    is_success,
)
from rest_framework.viewsets import ModelViewSet

from audit.cases.cases import get_audit_operation_and_object
from audit.cases.common import get_or_create_audit_obj
from audit.cef_logger import cef_logger
from audit.models import (
    MODEL_TO_AUDIT_OBJECT_TYPE_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObject,
    AuditOperation,
)
from cm.errors import AdcmEx
from cm.models import (
    Action,
    Cluster,
    ClusterBind,
    ClusterObject,
    Host,
    HostProvider,
    TaskLog,
)
from rbac.endpoints.group.serializers import GroupAuditSerializer
from rbac.endpoints.policy.serializers import PolicyAuditSerializer
from rbac.endpoints.role.serializers import RoleAuditSerializer
from rbac.endpoints.user.serializers import UserAuditSerializer
from rbac.models import Group, Policy, Role, User


def _get_view_and_request(args) -> tuple[View, Request]:
    if len(args) == 2:  # for audit view methods
        view: View = args[0]
        request: Request = args[1]
    else:  # for audit has_permissions method
        view: View = args[2]
        request: Request = args[1]

    return view, request


def _get_deleted_obj(view: View, request: Request, kwargs) -> Model | None:
    # pylint: disable=too-many-branches

    try:
        deleted_obj = view.get_object()
    except AssertionError:
        try:
            deleted_obj = view.get_obj(kwargs, kwargs["bind_id"])
        except AdcmEx:
            try:
                deleted_obj = view.queryset[0]
            except IndexError:
                deleted_obj = None
        except AttributeError:
            deleted_obj = None
    except (AdcmEx, Http404):  # when denied returns 404 from PermissionListMixin
        try:
            deleted_obj = view.queryset[0]
        except TypeError:
            if "role" in request.path:
                deleted_obj = Role.objects.filter(pk=view.kwargs["pk"]).first()
            else:
                deleted_obj = None
        except IndexError:
            deleted_obj = None
    except KeyError:
        deleted_obj = None
    except PermissionDenied:
        if "cluster_id" in kwargs:
            deleted_obj = Cluster.objects.filter(pk=kwargs["cluster_id"]).first()
        elif "service_id" in kwargs:
            deleted_obj = ClusterObject.objects.filter(pk=kwargs["service_id"]).first()
        else:
            deleted_obj = None

    return deleted_obj


def _get_object_changes(prev_data: dict, current_obj: Model) -> dict:
    serializer_class = None
    if isinstance(current_obj, Group):
        serializer_class = GroupAuditSerializer
    elif isinstance(current_obj, Role):
        serializer_class = RoleAuditSerializer
    elif isinstance(current_obj, User):
        serializer_class = UserAuditSerializer
    elif isinstance(current_obj, Policy):
        serializer_class = PolicyAuditSerializer

    if not serializer_class:
        return {}

    current_data = serializer_class(current_obj).data
    current_fields = {k: v for k, v in current_data.items() if prev_data[k] != v}
    if not current_fields:
        return current_fields

    object_changes = {
        "current": current_fields,
        "previous": {k: v for k, v in prev_data.items() if k in current_fields},
    }
    if object_changes["current"].get("password"):
        object_changes["current"]["password"] = "******"

    if object_changes["previous"].get("password"):
        object_changes["previous"]["password"] = "******"

    return object_changes


def _get_obj_changes_data(view: ModelViewSet) -> tuple[dict | None, Model | None]:
    prev_data = None
    current_obj = None
    serializer_class = None
    model = None
    if (
        isinstance(view, ModelViewSet)
        and view.action in {"update", "partial_update"}
        and view.kwargs.get("pk")
    ):
        if view.__class__.__name__ == "GroupViewSet":
            serializer_class = GroupAuditSerializer
            model = Group
        elif view.__class__.__name__ == "RoleViewSet":
            serializer_class = RoleAuditSerializer
            model = Role
        elif view.__class__.__name__ == "UserViewSet":
            serializer_class = UserAuditSerializer
            model = User
        elif view.__class__.__name__ == "PolicyViewSet":
            serializer_class = PolicyAuditSerializer
            model = Policy

        if serializer_class:
            current_obj = model.objects.filter(pk=view.kwargs["pk"]).first()
            prev_data = serializer_class(model.objects.filter(pk=view.kwargs["pk"]).first()).data
            if current_obj:
                prev_data = serializer_class(current_obj).data

    return prev_data, current_obj


def audit(func):
    # pylint: disable=too-many-statements
    @wraps(func)
    def wrapped(*args, **kwargs):
        # pylint: disable=too-many-branches,too-many-statements,too-many-locals

        audit_operation: AuditOperation
        audit_object: AuditObject
        operation_name: str
        view: View | ModelViewSet
        request: Request
        object_changes: dict

        error = None
        view, request = _get_view_and_request(args=args)

        if request.method == "DELETE":
            deleted_obj = _get_deleted_obj(view=view, request=request, kwargs=kwargs)
            if "bind_id" in kwargs:
                deleted_obj = ClusterBind.objects.filter(pk=kwargs["bind_id"]).first()
        else:
            deleted_obj = None

        prev_data, current_obj = _get_obj_changes_data(view=view)

        try:
            res = func(*args, **kwargs)
            if res is True:
                return res

            if res:
                status_code = res.status_code
            else:
                status_code = HTTP_403_FORBIDDEN
        except (AdcmEx, AdwpEx, ValidationError) as exc:
            error = exc
            res = None

            if getattr(exc, "msg", None) and (
                "doesn't exist" in exc.msg
                or "service is not installed in specified cluster" in exc.msg
            ):
                _kwargs = None
                if "cluster_id" in kwargs:
                    _kwargs = kwargs
                elif "cluster_id" in view.kwargs:
                    _kwargs = view.kwargs

                if _kwargs:
                    deleted_obj = Cluster.objects.filter(pk=_kwargs["cluster_id"]).first()

                if "provider_id" in kwargs and "host_id" in kwargs:
                    deleted_obj = Host.objects.filter(pk=kwargs["host_id"]).first()
                elif "provider_id" in view.kwargs:
                    deleted_obj = HostProvider.objects.filter(pk=view.kwargs["provider_id"]).first()

                if "service_id" in kwargs:
                    deleted_obj = ClusterObject.objects.filter(pk=kwargs["service_id"]).first()

                if "bind_id" in kwargs:
                    deleted_obj = ClusterBind.objects.filter(pk=kwargs["bind_id"]).first()

            if (
                getattr(exc, "msg", None)
                and "django model doesn't has __error_code__ attribute" in exc.msg
                and "task_id" in kwargs
            ):
                deleted_obj = TaskLog.objects.filter(pk=kwargs["task_id"]).first()

            if not deleted_obj:
                status_code = exc.status_code
                if (
                    status_code == HTTP_404_NOT_FOUND
                    and kwargs.get("action_id")
                    and Action.objects.filter(pk=kwargs["action_id"]).exists()
                ):
                    status_code = HTTP_403_FORBIDDEN

            else:  # when denied returns 404 from PermissionListMixin
                if getattr(exc, "msg", None) and (  # pylint: disable=too-many-boolean-expressions
                    "There is host" in exc.msg
                    or "belong to cluster" in exc.msg
                    or "of bundle" in exc.msg
                    or ("host doesn't exist" in exc.msg and not isinstance(deleted_obj, Host))
                ):
                    status_code = error.status_code
                else:
                    status_code = HTTP_403_FORBIDDEN
        except PermissionDenied as exc:
            status_code = HTTP_403_FORBIDDEN
            error = exc
            res = None
        except KeyError as exc:
            status_code = HTTP_400_BAD_REQUEST
            error = exc
            res = None

        audit_operation, audit_object, operation_name = get_audit_operation_and_object(
            view,
            res,
            deleted_obj,
        )
        if audit_operation:
            if is_success(status_code) and prev_data:
                current_obj.refresh_from_db()
                object_changes = _get_object_changes(prev_data=prev_data, current_obj=current_obj)
            else:
                object_changes = {}

            if is_success(status_code):
                operation_result = AuditLogOperationResult.Success
            elif status_code == HTTP_403_FORBIDDEN:
                operation_result = AuditLogOperationResult.Denied
            else:
                operation_result = AuditLogOperationResult.Fail

            if isinstance(view.request.user, DjangoUser):
                user = view.request.user
            else:
                user = None

            auditlog = AuditLog.objects.create(
                audit_object=audit_object,
                operation_name=operation_name,
                operation_type=audit_operation.operation_type,
                operation_result=operation_result,
                user=user,
                object_changes=object_changes,
            )
            cef_logger(audit_instance=auditlog, signature_id=resolve(request.path).route)

        if error:
            raise error

        return res

    return wrapped


def mark_deleted_audit_object(instance, object_type: str):
    audit_objs = []
    for audit_obj in AuditObject.objects.filter(object_id=instance.pk, object_type=object_type):
        audit_obj.is_deleted = True
        audit_objs.append(audit_obj)

    AuditObject.objects.bulk_update(objs=audit_objs, fields=["is_deleted"])


def make_audit_log(operation_type, result, operation_status):
    operation_type_map = {
        "task": {
            "type": AuditLogOperationType.Delete,
            "name": "\"Task log cleanup on schedule\" job",
        },
        "config": {
            "type": AuditLogOperationType.Delete,
            "name": "\"Objects configurations cleanup on schedule\" job",
        },
        "sync": {"type": AuditLogOperationType.Update, "name": "\"User sync on schedule\" job"},
        "audit": {
            "type": AuditLogOperationType.Delete,
            "name": "\"Audit log cleanup/archiving on schedule\" job",
        },
    }
    operation_name = operation_type_map[operation_type]["name"] + " " + operation_status
    system_user = User.objects.get(username="system")
    audit_log = AuditLog.objects.create(
        audit_object=None,
        operation_name=operation_name,
        operation_type=operation_type_map[operation_type]["type"],
        operation_result=result,
        user=system_user,
    )
    cef_logger(
        audit_instance=audit_log,
        signature_id="Background operation",
        empty_resource=True,
    )


def audit_finish_task(obj, operation_name: str, status: str) -> None:
    obj_type = MODEL_TO_AUDIT_OBJECT_TYPE_MAP.get(obj.__class__)
    if not obj_type:
        return

    audit_object = get_or_create_audit_obj(
        object_id=obj.pk,
        object_name=obj.name,
        object_type=obj_type,
    )
    if status == "success":
        operation_result = AuditLogOperationResult.Success
    else:
        operation_result = AuditLogOperationResult.Fail

    audit_log = AuditLog.objects.create(
        audit_object=audit_object,
        operation_name=operation_name,
        operation_type=AuditLogOperationType.Update,
        operation_result=operation_result,
        object_changes={},
    )

    cef_logger(audit_instance=audit_log, signature_id="Action completion")
