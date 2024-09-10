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

from collections import deque
from functools import wraps
from typing import Callable, Literal, Protocol

from django.contrib.auth.models import User as DjangoUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import F, Model
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from audit.alt.core import AuditedCallArguments, AuditHookFunc, OperationAuditContext, Result, RetrieveAuditObjectFunc
from audit.models import AuditLogOperationResult, AuditUser
from audit.utils import get_client_agent, get_client_ip


class HookObjectLookupFunc(Protocol):
    def __call__(self, id_: int) -> dict:
        ...


class AuditHook:
    """
    Convenience hook implementation to avoid specifying arguments each time.
    Accepts all regular arguments the hook will get in constructor,
    assigns them to attributes, then calls itself.

    This hook that does nothing if `__call__` isn't re-implemented.
    """

    __slots__ = ("context", "call_arguments", "result", "exception")

    def __init__(
        self,
        context: OperationAuditContext,
        call_arguments: AuditedCallArguments,
        result: Result | None,
        exception: Exception | None,
    ):
        self.context = context
        self.call_arguments = call_arguments
        self.result = result
        self.exception = exception
        self()

    def __call__(self):
        ...


# decorators to prepare / enhance / change hook


def only_on_success(func: AuditHookFunc) -> AuditHookFunc:
    @wraps(func)
    def wrapped(
        context: OperationAuditContext,
        call_arguments: AuditedCallArguments,
        result: Response | None,
        exception: Exception | None,
    ):
        if context.result != AuditLogOperationResult.SUCCESS:
            return None

        return func(context=context, call_arguments=call_arguments, result=result, exception=exception)

    return wrapped


def only_on_fail(func: AuditHookFunc) -> AuditHookFunc:
    @wraps(func)
    def wrapped(
        context: OperationAuditContext,
        call_arguments: AuditedCallArguments,
        result: Response | None,
        exception: Exception | None,
    ):
        if context.result == AuditLogOperationResult.SUCCESS:
            return None

        return func(context=context, call_arguments=call_arguments, result=result, exception=exception)

    return wrapped


def retriever_as_hook(func: RetrieveAuditObjectFunc) -> AuditHookFunc:
    """Call hook and assign its return value to object"""

    @wraps(func)
    def wrapped(
        context: OperationAuditContext,
        call_arguments: AuditedCallArguments,
        result: Response | None,
        exception: Exception | None,
    ) -> None:
        context.object = func(context=context, call_arguments=call_arguments, result=result, exception=exception)

    return wrapped


# basic hooks and hook builders


SECRET_FIELDS = ("password",)
SECRET_VALUE = "******"


def _hide_secrets(data: dict) -> dict:
    for field in data:
        if field in SECRET_FIELDS:
            data[field] = SECRET_VALUE

    return data


class cleanup_changes(AuditHook):
    """
    Clean up object changes stored in meta.
    Affects `current` and `previous` keys.
    """

    def __call__(self):
        changes = self.context.meta.changes

        if not changes:
            return

        current = changes.pop("current", {})
        previous = changes.pop("previous", {})

        if not (current or previous):
            return

        keys_to_remove = deque(maxlen=len(current))

        for key in current:
            # Since most extraction functions takes values from request/response,
            # "current" (being built from response) may have more keys than "previous" (due to PATCH),
            # so we need to remove this keys, because they weren't changed
            if key not in previous:
                keys_to_remove.append(key)

            elif previous[key] == current[key]:
                keys_to_remove.append(key)
                previous.pop(key)

        for key in keys_to_remove:
            current.pop(key)

        if current and previous:
            self.context.meta.changes |= {"previous": _hide_secrets(previous), "current": _hide_secrets(current)}


class detect_request_user(AuditHook):
    def __call__(self):
        request = self.call_arguments.get("request")
        if not hasattr(request, "user"):
            return

        if isinstance(request.user, DjangoUser):
            self.context.user = AuditUser.objects.filter(username=request.user.username).order_by("-pk").first()
        else:
            self.context.user = None


class collect_meta(AuditHook):
    def __call__(self):
        request = self.call_arguments.get("request")
        if not isinstance(request, WSGIRequest):
            return

        self.context.meta.address = get_client_ip(request)
        self.context.meta.agent = get_client_agent(request)


class set_api_operation_result(AuditHook):
    def __call__(self):
        # maybe set result will require something like "ensure object exists" on pre or collect hook before it,
        # but most likely `context.object` will be filled one way or another and will be enough for this function

        if not isinstance(self.result, Response):
            return

        if self.result.status_code < HTTP_400_BAD_REQUEST:
            self.context.result = AuditLogOperationResult.SUCCESS
        elif self.result.status_code in (HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN) or (
            self.result.status_code == HTTP_404_NOT_FOUND and self.context.object and not self.context.object.is_deleted
        ):
            self.context.result = AuditLogOperationResult.DENIED
        else:
            self.context.result = AuditLogOperationResult.FAIL


def adjust_denied_on_404_result(objects_exist: Callable[[AuditHook], bool]) -> AuditHookFunc:
    class HookImpl(set_api_operation_result):
        def __call__(self):
            if self.context.result == AuditLogOperationResult.DENIED and not objects_exist(self):
                self.context.result = AuditLogOperationResult.FAIL

    return HookImpl


@only_on_success
class mark_object_as_deleted_on_success(AuditHook):
    def __call__(self):
        if not self.context.object:
            return

        self.context.object.is_deleted = True
        self.context.object.save(update_fields=["is_deleted"])


# hook builders


def extract_previous_from_object(
    model: type[Model], *fields: str, id_field_: str = "pk", **named_fields: F
) -> AuditHookFunc:
    class HookImpl(AuditHook):
        def __call__(self):
            id_ = self.call_arguments.get(id_field_)
            if not id_:
                return

            model_data = model.objects.values(*fields, **named_fields).filter(id=id_).first() or {}
            self.context.meta.changes["previous"] = model_data

    return HookImpl


def extract_current_from_response(*fields: str, **named_fields: str) -> AuditHookFunc:
    class HookImpl(AuditHook):
        def __call__(self):
            if not isinstance(self.result, Response):
                return

            fields_ = (*tuple(zip(fields, fields)), *named_fields.items())

            data = self.result.data
            response_data = {audit_field: data[data_field] for audit_field, data_field in fields_ if data_field in data}

            self.context.meta.changes["current"] = response_data

    return HookImpl


def extract_from_object(
    func: HookObjectLookupFunc, section: Literal["current", "previous"], id_arg: str = "pk", id_field: str = "id"
):
    """
    Hook for cases when field is absent in response,
    or it is easier to get and format data with custom func than using orm lookups.
    Updates (or creates) self.context.meta.changes's `section` with `func` return value
    """

    class HookImpl(AuditHook):
        def __call__(self):
            id_ = self.call_arguments.get(id_arg) if section == "previous" else self.result.data.get(id_field)

            if id_ is None:
                return

            if section not in self.context.meta.changes:
                self.context.meta.changes[section] = {}

            self.context.meta.changes[section] |= func(id_=id_)

    return HookImpl


def extract_for_current_user(func: HookObjectLookupFunc, section: Literal["current", "previous"]):
    """
    Hook for retrieving user in requests to profile endpoints
    """

    class HookImpl(AuditHook):
        def __call__(self):
            id_ = self.context.user.id if self.context.user else None

            if id_ is None:
                return

            if section not in self.context.meta.changes:
                self.context.meta.changes[section] = {}

            self.context.meta.changes[section] |= func(id_=id_)

    return HookImpl
