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

from collections import UserDict
from dataclasses import dataclass, field
from typing import TypeAlias

from django.conf import settings  # TODO: maybe we should pass the version as a dependency?
from django.db.models import Model
from typing_extensions import Protocol, Self, TypeVar

from audit.cef_logger import cef_logger as write_cef_log
from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditUser,
)

Result = TypeVar("Result")
NameTemplate: TypeAlias = str
ObjectName: TypeAlias = str
OperationName: TypeAlias = str


class AuditConfigurationError(Exception):
    ...


@dataclass(slots=True, frozen=True)
class NameSplitterSettings:
    operation_name_max_len: int
    truncated_message: str = "...<truncated>"
    delimiter: str = ", "


@dataclass(slots=True, frozen=True)
class OperationNameTemplate:
    names: tuple[ObjectName, ...]
    template: NameTemplate


class NameSplitter(Protocol):
    def __call__(self: Self, name: OperationName | OperationNameTemplate) -> list[OperationName]:
        pass


@dataclass(slots=True)
class NameHalfSplitter:
    """
    Recursively splits object names in halves if final operation_name is longer than settings.operation_name_max_len.
    Truncates single object name if templating result exceeds this limit.
    Returns list of operation_names with partial sets of object names.
    """

    settings: NameSplitterSettings

    def __call__(self: Self, name: OperationName | OperationNameTemplate) -> list[OperationName]:
        if isinstance(name, OperationName):
            return [name]

        return self._split_names(template=name)

    def _split_names(self: Self, template: OperationNameTemplate) -> list[OperationName]:
        names = template.names
        template = template.template

        operation_name = template.format(self.settings.delimiter.join(names))
        if len(operation_name) <= self.settings.operation_name_max_len:
            return [operation_name]

        if len(names) == 1:
            template_len = len(template.format(""))
            truncated_msg_len = len(self.settings.truncated_message)
            rest_len = self.settings.operation_name_max_len - (template_len + truncated_msg_len)

            if rest_len <= 0:
                # This situation is unlikely to happen, since op_name_max_len = 2000
                # We don't want to check model's limits at import time in decorator, so it takes place here
                err_msg = (
                    f"Can't truncate object's name `{names[0]}` to suite operation_name field max length. "
                    f"Adjust some of the following: {template_len=}, {truncated_msg_len=}, "
                    f"operation_name_len={self.settings.operation_name_max_len}"
                )
                raise AuditConfigurationError(err_msg)

            name = f"{names[0][:rest_len]}{self.settings.truncated_message}"
            return [template.format(name)]

        mid = len(names) // 2
        left = OperationNameTemplate(names=names[:mid], template=template)
        right = OperationNameTemplate(names=names[mid:], template=template)

        return self._split_names(template=left) + self._split_names(template=right)


def build_name_splitter_settings_from_django_models() -> NameSplitterSettings:
    operation_name_max_len = AuditLog._meta.get_field("operation_name").max_length

    return NameSplitterSettings(operation_name_max_len=operation_name_max_len)


class AuditedCallArguments(UserDict):
    """
    Simple and dummy implementation for "frozendict" to prevent accidental changes to call arguments
    """

    def __setitem__(self, key, value):
        message = "Audit context can't be changed"
        raise ValueError(message)

    def set(self, from_dict: dict) -> Self:
        """The only "correct" way to assign data to the context dict"""
        self.data = from_dict
        return self


@dataclass(slots=True, frozen=False)
class AuditedCall:
    arguments: AuditedCallArguments = field(default_factory=AuditedCallArguments)
    result: Result | None = None
    exception: Exception | None = None


@dataclass(slots=True, frozen=False)
class OperationMeta:
    address: str | None = None
    agent: str = ""
    changes: dict = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class AuditSignature:
    id: str
    type: AuditLogOperationType


class AuditHookFunc(Protocol):
    def __call__(
        self,
        *,
        context: "OperationAuditContext",
        call_arguments: AuditedCallArguments,
        result: Result | None,
        exception: Exception | None,
    ):
        ...


class RetrieveAuditObjectFunc(Protocol):
    def __call__(
        self,
        *,
        context: "OperationAuditContext",
        call_arguments: AuditedCallArguments,
        result: Result | None,
        exception: Exception | None,
    ) -> AuditObject | None:
        ...


@dataclass(slots=True, frozen=True)
class Hooks:
    pre_call: tuple[AuditHookFunc, ...] = ()
    """
    Thou `pre_call` hooks have `result` and `exception` arguments,
    but they should be expected to be `None` always
    """

    on_collect: tuple[AuditHookFunc, ...] = ()

    def __add__(self, other: "Hooks") -> Self:
        if not isinstance(other, Hooks):
            message = f"{other} should be of `Hooks` type"
            raise TypeError(message)

        return Hooks(pre_call=(*self.pre_call, *other.pre_call), on_collect=(*self.on_collect, *other.on_collect))


class OperationAuditContext:
    """
    Audited operation context that accumulates input arguments and allow basic flow control.

    Actual behavior and attributes changes should be configured via hooks.
    DEFAULT_HOOKS have priority over user-provided.
    Knowledge of what work is performed on which method calls is advised.

    Also note that:
    - Pre-call hooks have `result` and `exception` equal to None
    - Thou `retrieve_object` and hooks have very similar API, it isn't expected from hook to return anything,
      but `retrieve_object` is expected to return value or None if it can't be returned
    - `retrieve_object`'s return value is assigned to `object` attribute unconditionally during `collect` call
    - Hooks should be as safe as possible (raise no Exceptions)
    """

    DEFAULT_HOOKS = Hooks()

    name: OperationName | OperationNameTemplate
    result: AuditLogOperationResult
    meta: OperationMeta

    object: AuditObject | None
    user: AuditUser | None

    _call: AuditedCall
    _retrieve_object: RetrieveAuditObjectFunc
    _name_splitter: NameSplitter

    def __init__(
        self,
        signature: AuditSignature,
        default_name: str,
        retrieve_object: RetrieveAuditObjectFunc,
        custom_hooks: Hooks,
        name_splitter: NameSplitter,
    ):
        self._default_name = default_name
        self._signature = signature
        self._hooks = self.DEFAULT_HOOKS + custom_hooks
        self._retrieve_object = retrieve_object
        self._name_splitter = name_splitter

        self.restore_defaults()

    @property
    def signature(self) -> AuditSignature:
        return self._signature

    def restore_defaults(self) -> Self:
        self.name = self._default_name
        self.result = AuditLogOperationResult.FAIL
        self.object: AuditObject | None = None
        self.user: AuditUser | None = None
        self.meta = OperationMeta()
        self._call = AuditedCall()
        return self

    def attach_call_arguments(self, arguments: dict) -> Self:
        self._call.arguments.set(from_dict=arguments)
        return self

    def attach_result(self, result: Result | None) -> Self:
        self._call.result = result
        return self

    def attach_exception(self, exception: Exception | None) -> Self:
        self._call.exception = exception
        return self

    def run_pre_call_hooks(self) -> Self:
        for hook in self._hooks.pre_call:
            hook(context=self, call_arguments=self._call.arguments, result=None, exception=None)

        return self

    def collect(self) -> Self:
        self.object = self._retrieve_object(
            context=self, call_arguments=self._call.arguments, result=self._call.result, exception=self._call.exception
        )

        for hook in self._hooks.on_collect:
            hook(
                context=self,
                call_arguments=self._call.arguments,
                result=self._call.result,
                exception=self._call.exception,
            )

        return self

    def save(self) -> None:
        operation_names = self._name_splitter(name=self.name)

        for operation_name in operation_names:
            record = AuditLog.objects.create(
                audit_object=self.object,
                operation_name=operation_name,
                operation_type=self._signature.type,
                operation_result=self.result,
                user=self.user,
                object_changes=self.meta.changes,
                address=self.meta.address,
                agent=self.meta.agent,
            )
            write_cef_log(audit_instance=record, signature_id=self._signature.id, adcm_version=settings.ADCM_VERSION)


@dataclass(slots=True)
class IDBasedAuditObjectCreator:
    model: type[Model]
    name_field: str = "name"

    def __call__(self, id_: str | int, audit_object_type: AuditObjectType) -> AuditObject | None:
        name = self.get_name(id_=id_)
        if not name:
            return None

        return AuditObject.objects.create(object_id=id_, object_type=audit_object_type, object_name=name)

    def get_name(self, id_: str | int) -> str | None:
        return self.model.objects.values_list(self.name_field, flat=True).filter(id=id_).first()
