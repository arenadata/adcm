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

import re
from contextlib import suppress
from functools import wraps

from api.cluster.serializers import ClusterAuditSerializer
from api.component.serializers import ComponentAuditSerializer
from api.host.serializers import HostAuditSerializer
from api.service.serializers import ServiceAuditSerializer
from api_v2.cluster.serializers import (
    ClusterAuditSerializer as ClusterAuditSerializerV2,
)
from api_v2.component.serializers import (
    ComponentAuditSerializer as ComponentAuditSerializerV2,
)
from api_v2.host.serializers import HostAuditSerializer as HostAuditSerializerV2
from api_v2.host.serializers import HostChangeMaintenanceModeSerializer
from api_v2.service.serializers import (
    ServiceAuditSerializer as ServiceAuditSerializerV2,
)
from api_v2.views import CamelCaseModelViewSet
from audit.cases.cases import get_audit_operation_and_object
from audit.cef_logger import cef_logger
from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObject,
    AuditOperation,
    AuditUser,
)
from cm.errors import AdcmEx
from cm.models import (
    Action,
    Cluster,
    ClusterBind,
    ClusterObject,
    Host,
    HostProvider,
    ServiceComponent,
    TaskLog,
    Upgrade,
    get_cm_model_by_type,
    get_model_by_type,
)
from django.contrib.auth.models import User as DjangoUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Model, ObjectDoesNotExist
from django.http.response import Http404
from django.urls import resolve
from rbac.endpoints.group.serializers import GroupAuditSerializer
from rbac.endpoints.policy.serializers import PolicyAuditSerializer
from rbac.endpoints.role.serializers import RoleAuditSerializer
from rbac.endpoints.user.serializers import UserAuditSerializer
from rbac.models import Group, Policy, Role, User, get_rbac_model_by_type
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    is_success,
)
from rest_framework.viewsets import ModelViewSet

AUDITED_HTTP_METHODS = frozenset(("POST", "DELETE", "PUT", "PATCH"))

URL_PATH_PATTERN = re.compile(r".*/api/v(?P<api_version>\d+)/(?P<target_path>.*?)/?$")


def _are_all_parents_in_path_exist(view: GenericAPIView) -> bool:
    for pk, val in view.kwargs.items():
        model = get_model_by_type(pk.rstrip("_pk"))
        if not model.objects.filter(pk=val).exists():
            return False
    return True


def _get_view_and_request(args) -> tuple[GenericAPIView, WSGIRequest]:
    if len(args) == 2:  # for audit view methods
        view: GenericAPIView = args[0]
        request: WSGIRequest = args[1]
    else:  # for audit has_permissions method
        view: GenericAPIView = args[2]
        request: WSGIRequest = args[1]

    return view, request


def _get_deleted_obj(
    view: GenericAPIView, request: WSGIRequest, kwargs: dict, api_version: int, path: list[str]
) -> Model | None:
    # pylint: disable=too-many-branches, too-many-statements

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
    except (AdcmEx, Http404) as e:  # when denied returns 404 from PermissionListMixin
        if api_version == 1:
            try:
                if getattr(view, "queryset") is None:
                    raise TypeError from e

                if view.queryset.count() == 1:
                    deleted_obj = view.queryset.all()[0]
                elif "pk" in view.kwargs:
                    try:
                        deleted_obj = view.queryset.get(pk=int(view.kwargs["pk"]))
                    except ValueError:
                        deleted_obj = None
                else:
                    deleted_obj = None
            except TypeError:
                if "role" in request.path:
                    deleted_obj = Role.objects.filter(pk=view.kwargs["pk"]).first()
                else:
                    deleted_obj = None
            except (IndexError, ObjectDoesNotExist):
                deleted_obj = None
        elif api_version == 2:
            deleted_obj = get_target_object_by_path(path=path)
        else:
            raise ValueError(f"Unexpected api version: `{api_version}`") from e
    except (KeyError, ValueError):
        deleted_obj = None
    except PermissionDenied as e:
        deleted_obj = None

        if api_version == 1:
            if "cluster_id" in kwargs:
                deleted_obj = Cluster.objects.filter(pk=kwargs["cluster_id"]).first()
            elif "service_id" in kwargs:
                deleted_obj = ClusterObject.objects.filter(pk=kwargs["service_id"]).first()
            elif "provider_id" in kwargs:
                deleted_obj = HostProvider.objects.filter(pk=kwargs["provider_id"]).first()

        elif api_version == 2:
            deleted_obj = get_target_object_by_path(path=path)

        else:
            raise ValueError(f"Unexpected api version: `{api_version}`") from e

    return deleted_obj


def get_target_object_by_path(path: list[str]) -> Model | None:
    result = get_target_model_and_id_by_path(path=path)
    if result is None:
        return None

    try:
        model, pk = result
        return model.objects.filter(pk=int(pk)).first()
    except ValueError:
        return None


def get_target_model_and_id_by_path(  # pylint: disable=too-many-return-statements
    path: list[str],
) -> tuple[type[Model], str] | None:
    match path:
        case ["rbac", rbac_type, pk]:
            try:
                model = get_rbac_model_by_type(rbac_type)
                return model, pk
            except KeyError:
                return None
        case ["audit", *_]:
            return None
        case [*_, "actions", pk, "run"]:
            return Action, pk
        case [*_, "upgrades", pk, "run"]:
            return Upgrade, pk
        case (
            ["clusters" | "hostproviders" | "hosts", pk]
            | ["clusters" | "hosts", pk, _]  # here will be actions on objects like mapping, mm, adding services, etc.
        ):
            try:
                return get_cm_model_by_type(path[0].rstrip("s")), pk
            except KeyError:
                return None
        case [*_, "hosts", pk] | [*_, "hosts", pk, _]:
            # also for mm on hosts and update of nested host entries in cluster
            return Host, pk
        case (
            [*_, cm_type, pk, "mapping" | "imports" | "maintenance-mode" | "configs" | "config-groups" | "terminate"]
            | ["clusters" | "hosts" | "hostproviders", _, *_, cm_type, pk]
        ):
            try:
                # here will be also config, config groups, basic actions, etc.
                return get_cm_model_by_type(cm_type.rstrip("s")), pk
            except KeyError:
                return None
        case _:
            return None


# pylint: disable=too-many-branches
def _get_object_changes(prev_data: dict, current_obj: Model, api_version: int) -> dict:
    serializer_class = None
    if isinstance(current_obj, Group):
        serializer_class = GroupAuditSerializer
    elif isinstance(current_obj, Role):
        serializer_class = RoleAuditSerializer
    elif isinstance(current_obj, User):
        serializer_class = UserAuditSerializer
    elif isinstance(current_obj, Policy):
        serializer_class = PolicyAuditSerializer
    elif isinstance(current_obj, Cluster):
        if api_version == 1:
            serializer_class = ClusterAuditSerializer
        elif api_version == 2:
            serializer_class = ClusterAuditSerializerV2
    elif isinstance(current_obj, Host):
        if api_version == 1:
            serializer_class = HostAuditSerializer
        elif api_version == 2:
            serializer_class = HostAuditSerializerV2
    elif isinstance(current_obj, ClusterObject):
        if api_version == 1:
            serializer_class = ServiceAuditSerializer
        elif api_version == 2:
            serializer_class = ServiceAuditSerializerV2
    elif isinstance(current_obj, ServiceComponent):
        if api_version == 1:
            serializer_class = ComponentAuditSerializer
        elif api_version == 2:
            serializer_class = ComponentAuditSerializerV2

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


def _get_obj_changes_data(view: GenericAPIView | ModelViewSet) -> tuple[dict | None, Model | None]:
    # pylint: disable=too-many-branches,too-many-statements

    prev_data = None
    current_obj = None
    serializer_class = None
    pk = None

    if (
        isinstance(view, (ModelViewSet, CamelCaseModelViewSet))
        and view.action in {"update", "partial_update"}
        and view.kwargs.get("pk")
    ):
        pk = view.kwargs["pk"]
        if view.__class__.__name__ == "GroupViewSet":
            serializer_class = GroupAuditSerializer
        elif view.__class__.__name__ == "RoleViewSet":
            serializer_class = RoleAuditSerializer
        elif view.__class__.__name__ == "UserViewSet":
            serializer_class = UserAuditSerializer
        elif view.__class__.__name__ == "PolicyViewSet":
            serializer_class = PolicyAuditSerializer
        elif view.__class__.__name__ == "ClusterViewSet":
            serializer_class = ClusterAuditSerializerV2
    elif view.request.method in {"PATCH", "PUT"}:
        if view.__class__.__name__ == "ClusterDetail":
            serializer_class = ClusterAuditSerializer
            pk = view.kwargs["cluster_id"]
        elif view.__class__.__name__ == "HostDetail":
            serializer_class = HostAuditSerializer
            pk = view.kwargs["host_id"]
    elif view.request.method == "POST":
        if view.__class__.__name__ == "ServiceMaintenanceModeView":
            serializer_class = ServiceAuditSerializer
            pk = view.kwargs["service_id"]
        elif view.__class__.__name__ == "HostMaintenanceModeView":
            serializer_class = HostAuditSerializer
            pk = view.kwargs["host_id"]
        elif view.__class__.__name__ == "ComponentMaintenanceModeView":
            serializer_class = ComponentAuditSerializer
            pk = view.kwargs["component_id"]
        elif view.__class__.__name__ == "HostClusterViewSet" and view.action == "maintenance_mode":
            serializer_class = HostAuditSerializerV2
            pk = view.kwargs["pk"]
        elif view.__class__.__name__ == "HostViewSet" and view.action == "maintenance_mode":
            serializer_class = HostChangeMaintenanceModeSerializer
            pk = view.kwargs["pk"]
        elif view.__class__.__name__ == "ServiceViewSet" and view.action == "maintenance_mode":
            serializer_class = ServiceAuditSerializerV2
            pk = view.kwargs["pk"]
        elif view.__class__.__name__ == "ComponentViewSet" and view.action == "maintenance_mode":
            serializer_class = ComponentAuditSerializerV2
            pk = view.kwargs["pk"]

    if serializer_class:
        if hasattr(view, "audit_model_hint"):  # for cases when get_queryset() raises error
            model = view.audit_model_hint
        else:
            model = view.get_queryset().model

        try:
            current_obj = model.objects.filter(pk=pk).first()
            prev_data = serializer_class(model.objects.filter(pk=pk).first()).data
        except ValueError:
            current_obj = None
            prev_data = None

        if current_obj:
            prev_data = serializer_class(current_obj).data

    return prev_data, current_obj


def _parse_path(path: str) -> tuple[int, list[str]]:
    match = URL_PATH_PATTERN.match(string=path)
    if match is None:
        return -1, []

    return int(match.group("api_version")), match.group("target_path").split(sep="/")


def _detect_deleted_object_for_v1(
    error: AdcmEx | ValidationError | Http404 | NotFound, view, request, previously_detected_object, kwargs
):
    deleted_obj = previously_detected_object
    if getattr(error, "msg", None) and (
        "doesn't exist" in error.msg or "service is not installed in specified cluster" in error.msg
    ):
        _kwargs = None
        if "cluster_id" in kwargs:
            _kwargs = kwargs
        elif "cluster_id" in view.kwargs:
            _kwargs = view.kwargs

        if _kwargs and "maintenance-mode" not in request.path:
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
        getattr(error, "msg", None)
        and "django model doesn't has __error_code__ attribute" in error.msg
        and "task_id" in kwargs
    ):
        deleted_obj = TaskLog.objects.filter(pk=kwargs["task_id"]).first()

    return deleted_obj


def _detect_status_code_and_deleted_object_for_v1(
    error: AdcmEx | ValidationError | Http404 | NotFound, deleted_obj, kwargs
) -> int:
    if not deleted_obj:
        if isinstance(error, Http404):
            status_code = HTTP_404_NOT_FOUND
        else:
            status_code = error.status_code

        if status_code != HTTP_404_NOT_FOUND:
            return status_code

        action_perm_denied = kwargs.get("action_id") and Action.objects.filter(pk=kwargs["action_id"]).exists()
        task_perm_denied = kwargs.get("task_pk") and TaskLog.objects.filter(pk=kwargs["task_pk"]).exists()
        if action_perm_denied or task_perm_denied:
            return HTTP_403_FORBIDDEN

        return status_code

    # when denied returns 404 from PermissionListMixin
    if getattr(error, "msg", None) and (  # pylint: disable=too-many-boolean-expressions
        "There is host" in error.msg
        or "belong to cluster" in error.msg
        or "host associated with a cluster" in error.msg
        or "of bundle" in error.msg
        or ("host doesn't exist" in error.msg and not isinstance(deleted_obj, Host))
    ):
        return error.status_code

    if isinstance(error, ValidationError):
        return error.status_code

    return HTTP_403_FORBIDDEN


def _cm_object_exists(path_type: str, pk: str) -> bool:
    try:
        model = get_cm_model_by_type(object_type=path_type.rstrip("s"))
    except KeyError:
        return False

    try:
        return model.objects.filter(pk=int(pk)).exists()
    except ValueError:
        return False


def _all_child_objects_exist(path: list[str]) -> bool:
    match path:
        case ["configs", pk]:
            return _cm_object_exists(path_type="configs", pk=pk)
        case ["services" | "components" | "hosts" | "config-groups" | "actions" | "upgrades", pk, *rest]:
            if not _cm_object_exists(path_type=path[0], pk=pk):
                return False
            return _all_child_objects_exist(path=rest)
        case _:
            return True


def _all_objects_in_path_exist(path: list[str]) -> bool:  # pylint: disable=too-many-return-statements
    match path:
        case ["rbac", rbac_type, pk, *_]:
            with suppress(KeyError, ValueError):
                model = get_rbac_model_by_type(rbac_type)
                return model.objects.filter(pk=pk).exists()
            return False
        case ["clusters" | "hostproviders" | "hosts" | "bundles" | "prototypes", pk, *rest]:
            if not _cm_object_exists(path_type=path[0], pk=pk):
                return False
            return _all_child_objects_exist(path=rest)
        case ["tasks" | "jobs", pk, *_]:
            return _cm_object_exists(path_type=path[0], pk=pk)
        case ["adcm", *rest]:
            return _all_child_objects_exist(path=rest)
        case _:
            return True


def audit(func):
    # pylint: disable=too-many-statements
    @wraps(func)
    def wrapped(*args, **kwargs):
        # pylint: disable=too-many-branches,too-many-statements,too-many-locals

        audit_operation: AuditOperation
        audit_object: AuditObject
        operation_name: str
        view: GenericAPIView | ModelViewSet
        request: WSGIRequest
        object_changes: dict

        error = None
        view, request = _get_view_and_request(args=args)
        api_version, path = _parse_path(path=view.request.path)
        if request.method not in AUDITED_HTTP_METHODS or api_version == -1:
            return func(*args, **kwargs)

        # If request should be audited, here comes the preparation part

        deleted_obj = None
        if request.method == "DELETE":
            deleted_obj = _get_deleted_obj(
                view=view, request=request, kwargs=kwargs, api_version=api_version, path=path
            )
            if "bind_id" in kwargs and api_version == 1:
                deleted_obj = ClusterBind.objects.filter(pk=kwargs["bind_id"]).first()
        elif api_version == 1:
            if "host_id" in kwargs and "maintenance-mode" in request.path:
                deleted_obj = Host.objects.filter(pk=kwargs["host_id"]).first()
            elif "service_id" in kwargs and "maintenance-mode" in request.path:
                deleted_obj = ClusterObject.objects.filter(pk=kwargs["service_id"]).first()
            elif "component_id" in kwargs and "maintenance-mode" in request.path:
                deleted_obj = ServiceComponent.objects.filter(pk=kwargs["component_id"]).first()

        prev_data, current_obj = _get_obj_changes_data(view=view)

        # Now we process audited function

        try:
            res = func(*args, **kwargs)
            if res is True:
                return res

            # Correctly finished request (when will be `bool(res) is False`?)
            if res:
                status_code = res.status_code
            else:
                status_code = HTTP_403_FORBIDDEN
        except (AdcmEx, ValidationError, Http404, NotFound) as exc:
            error = exc
            res = None

            if api_version == 2:
                if isinstance(error, Http404):
                    status_code = HTTP_404_NOT_FOUND
                else:
                    status_code = error.status_code

                if status_code == HTTP_404_NOT_FOUND and _all_objects_in_path_exist(path=path):
                    status_code = HTTP_403_FORBIDDEN

            else:
                deleted_obj = _detect_deleted_object_for_v1(
                    error=error, view=view, request=request, previously_detected_object=deleted_obj, kwargs=kwargs
                )
                status_code = _detect_status_code_and_deleted_object_for_v1(
                    error=error,
                    deleted_obj=deleted_obj,
                    kwargs=kwargs,
                )

        except PermissionDenied as exc:
            status_code = HTTP_403_FORBIDDEN
            error = exc
            res = None

        except KeyError as exc:
            status_code = HTTP_400_BAD_REQUEST
            error = exc
            res = None

        audit_operation, audit_object, operation_name = get_audit_operation_and_object(
            view=view, response=res, deleted_obj=deleted_obj, path=path, api_version=api_version
        )
        if audit_operation:
            if is_success(status_code) and prev_data:
                current_obj.refresh_from_db()
                object_changes = _get_object_changes(
                    prev_data=prev_data, current_obj=current_obj, api_version=api_version
                )
            else:
                object_changes = {}

            if is_success(status_code):
                operation_result = AuditLogOperationResult.SUCCESS
            elif status_code == HTTP_403_FORBIDDEN:
                operation_result = AuditLogOperationResult.DENIED
            else:
                operation_result = AuditLogOperationResult.FAIL

            if isinstance(view.request.user, DjangoUser):
                audit_user = AuditUser.objects.filter(username=view.request.user.username).order_by("-pk").first()
            else:
                audit_user = None

            auditlog = AuditLog.objects.create(
                audit_object=audit_object,
                operation_name=operation_name,
                operation_type=audit_operation.operation_type,
                operation_result=operation_result,
                user=audit_user,
                object_changes=object_changes,
                address=get_client_ip(request=request),
            )
            cef_logger(audit_instance=auditlog, signature_id=resolve(request.path).route)

        if error:
            raise error

        return res

    return wrapped


def make_audit_log(operation_type, result, operation_status):
    operation_type_map = {
        "task": {
            "type": AuditLogOperationType.DELETE,
            "name": '"Task log cleanup on schedule" job',
        },
        "config": {
            "type": AuditLogOperationType.DELETE,
            "name": '"Objects configurations cleanup on schedule" job',
        },
        "sync": {"type": AuditLogOperationType.UPDATE, "name": '"User sync on schedule" job'},
        "audit": {
            "type": AuditLogOperationType.DELETE,
            "name": '"Audit log cleanup/archiving on schedule" job',
        },
        "statistics": {"type": "", "name": '"Statistics collection on schedule" job'},
    }
    operation_name = operation_type_map[operation_type]["name"] + " " + operation_status
    audit_log = AuditLog.objects.create(
        audit_object=None,
        operation_name=operation_name,
        operation_type=operation_type_map[operation_type]["type"],
        operation_result=result,
        user=AuditUser.objects.get(username="system"),
    )
    cef_logger(audit_instance=audit_log, signature_id="Background operation", empty_resource=True)


def get_client_ip(request: WSGIRequest) -> str | None:
    header_fields = ["HTTP_X_FORWARDED_FOR", "HTTP_X_FORWARDED_HOST", "HTTP_X_FORWARDED_SERVER", "REMOTE_ADDR"]
    host = None

    for field in header_fields:
        if field in request.META:
            host = request.META[field].split(",")[-1]
            break

    return host
