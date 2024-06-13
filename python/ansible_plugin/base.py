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

from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Collection, Generic, Literal, Mapping, Protocol, TypeAlias, TypeVar
import fcntl
import traceback

try:  # TODO: refactor when python >= 3.11
    from typing import Self
except ImportError:
    from typing_extensions import Self

from ansible.errors import AnsibleActionFail
from ansible.module_utils._text import to_native
from ansible.plugins.action import ActionBase
from cm.converters import core_type_to_model
from cm.models import Cluster, ClusterObject, Host, HostProvider, ServiceComponent
from core.types import ADCMCoreType, CoreObjectDescriptor, ObjectID
from django.conf import settings
from django.db.models import ObjectDoesNotExist
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ansible_plugin.errors import (
    ADCMPluginError,
    PluginContextError,
    PluginRuntimeError,
    PluginTargetDetectionError,
    PluginValidationError,
    compose_validation_error_details_message,
)


class BaseStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Input


TargetTypeLiteral = Literal["cluster", "service", "component", "provider", "host"]
ProductORMObject: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider | Host


class VarsContextSection(BaseModel):
    """
    Context from `config.json`'s `context` section
    (actually from "vars" available during ansible run)
    """

    type: TargetTypeLiteral
    cluster_id: int | None = None
    service_id: int | None = None
    component_id: int | None = None
    provider_id: int | None = None
    host_id: int | None = None

    @field_validator("type", mode="before")
    @classmethod
    def convert_type_to_string(cls, v: Any) -> str:
        # requited to pre-process Ansible Strings
        return str(v)


class VarsJobSection(BaseModel):
    """
    Job related info from ansible runtime vars' "job" dictionary
    """

    id: ObjectID
    action: str


class AnsibleRuntimeVars(BaseModel):
    """
    Container for ansible runtime variables required for plugin execution
    """

    context: VarsContextSection
    job: VarsJobSection


class RuntimeEnvironment(BaseModel):
    """
    Container for things dependent on ansible runtime
    """

    context_owner: CoreObjectDescriptor
    vars: AnsibleRuntimeVars


# Target


class ObjectWithType(BaseStrictModel):
    type: TargetTypeLiteral

    @field_validator("type", mode="before")
    @classmethod
    def convert_type_to_string(cls, v: Any) -> str:
        # requited to pre-process Ansible Strings
        return str(v)


class CoreObjectTargetDescription(ObjectWithType):
    service_name: str | None = None
    component_name: str | None = None
    host_id: int | str | None = None

    @model_validator(mode="after")
    def validate_args_allowed_for_type(self) -> Self:
        match self.type:
            case "cluster":
                forbidden = ("service_name", "component_name", "host_id")
            case "service":
                forbidden = ("component_name", "host_id")
            case "component":
                forbidden = ("host_id",)
            case "provider":
                forbidden = ("service_name", "component_name", "host_id")
            case "host":
                forbidden = ("service_name", "component_name")
            case _:
                raise PluginTargetDetectionError(f"Unsupported type: {self.type}")

        if error_fields := [field for field in forbidden if getattr(self, field) is not None]:
            message = f"{', '.join(error_fields)} option(s) is not allowed for {self.type} type"
            raise ValueError(message)

        return self

    def __str__(self) -> str:
        return ", ".join(f"{key}='value'" for key, value in self.model_dump(exclude_none=True))


class BaseTypedArguments(CoreObjectTargetDescription):
    pass


class BaseArgumentsWithTypedObjects(BaseStrictModel):
    objects: list[CoreObjectTargetDescription] = Field(default_factory=list)


class TargetDetector(Protocol):
    def __call__(
        self,
        context_owner: CoreObjectDescriptor,
        context: VarsContextSection,
        parsed_arguments: Any,
    ) -> tuple[CoreObjectDescriptor, ...]:
        ...


def from_objects(
    context_owner: CoreObjectDescriptor,  # noqa: ARG001
    context: VarsContextSection,
    parsed_arguments: Any,
) -> tuple[CoreObjectDescriptor, ...]:
    if not isinstance(parsed_arguments, BaseArgumentsWithTypedObjects):
        return ()

    return tuple(
        _from_target_description(target_description=target_description, context=context)
        for target_description in parsed_arguments.objects
    )


def from_arguments_root(
    context_owner: CoreObjectDescriptor,  # noqa: ARG001
    context: VarsContextSection,
    parsed_arguments: Any,
) -> tuple[CoreObjectDescriptor, ...]:
    if not isinstance(parsed_arguments, BaseTypedArguments):
        return ()

    return (_from_target_description(target_description=parsed_arguments, context=context),)


def from_context(
    context_owner: CoreObjectDescriptor,
    context: VarsContextSection,  # noqa: ARG001
    parsed_arguments: Any,  # noqa: ARG001
) -> tuple[CoreObjectDescriptor, ...]:
    return (context_owner,)


def _from_target_description(
    target_description: CoreObjectTargetDescription, context: VarsContextSection
) -> CoreObjectDescriptor:
    match target_description.type:
        case "cluster":
            if context.cluster_id:
                return CoreObjectDescriptor(id=context.cluster_id, type=ADCMCoreType.CLUSTER)

            message = "Can't identify cluster from context"
            raise PluginRuntimeError(message=message)

        case "service":
            if target_description.service_name:
                if not context.cluster_id:
                    message = "Can't identify service by name without `cluster_id` in context"
                    raise PluginRuntimeError(message=message)

                return CoreObjectDescriptor(
                    id=ClusterObject.objects.values_list("id", flat=True).get(
                        cluster_id=context.cluster_id, prototype__name=target_description.service_name
                    ),
                    type=ADCMCoreType.SERVICE,
                )

            if context.service_id:
                return CoreObjectDescriptor(id=context.service_id, type=ADCMCoreType.SERVICE)

            message = f"Can't identify service based on arguments: {target_description}"
            raise PluginRuntimeError(message=message)

        case "component":
            if target_description.component_name:
                if not context.cluster_id:
                    message = "Can't identify component by name without `cluster_id` in context"
                    raise PluginRuntimeError(message=message)

                component_id_qs = ServiceComponent.objects.values_list("id", flat=True)
                kwargs = {"cluster_id": context.cluster_id, "prototype__name": target_description.component_name}
                if target_description.service_name:
                    return CoreObjectDescriptor(
                        id=component_id_qs.get(**kwargs, service__prototype__name=target_description.service_name),
                        type=ADCMCoreType.COMPONENT,
                    )

                if context.service_id:
                    return CoreObjectDescriptor(
                        id=component_id_qs.get(**kwargs, service_id=context.service_id),
                        type=ADCMCoreType.COMPONENT,
                    )

                message = "Can't identify component by name without `service_name` or out of service context"
                raise PluginRuntimeError(message=message)

            if context.component_id:
                return CoreObjectDescriptor(id=context.component_id, type=ADCMCoreType.COMPONENT)

            message = f"Can't identify component based on arguments: {target_description}"
            raise PluginRuntimeError(message=message)

        case "provider":
            if context.provider_id:
                return CoreObjectDescriptor(id=context.provider_id, type=ADCMCoreType.HOSTPROVIDER)

            message = "Can't identify hostprovider from context"
            raise PluginRuntimeError(message=message)

        case "host":
            if target_description.host_id:
                return CoreObjectDescriptor(id=int(target_description.host_id), type=ADCMCoreType.HOST)

            if context.host_id:
                return CoreObjectDescriptor(id=context.host_id, type=ADCMCoreType.HOST)

            message = "Can't identify host from context"
            raise PluginRuntimeError(message=message)

        case _:
            message = f"Can't identify object of type {target_description.type}"
            raise PluginRuntimeError(message=message)


def retrieve_orm_object(
    object_: CoreObjectDescriptor, error_class: type[ADCMPluginError] = PluginTargetDetectionError
) -> ProductORMObject:
    try:
        return core_type_to_model(core_type=object_.type).objects.get(pk=object_.id)
    except ObjectDoesNotExist:
        raise error_class(message=f'Failed to locate {object_.type} with id "{object_.id}"') from None


# Plugin

CallArguments = TypeVar("CallArguments", bound=BaseModel)
ReturnValue = TypeVar("ReturnValue")


class NoArguments(BaseModel):
    """
    Use it when plugin doesn't use any arguments
    """


@dataclass(frozen=True, slots=True)
class CallResult(Generic[ReturnValue]):
    # If value is a mapping of some sort, it'll be unpacked into return dict.
    # If it is `None`, nothing will be added to response dictionary.
    # Otherwise, value will be placed under the "value" key.
    value: ReturnValue | None
    changed: bool
    error: ADCMPluginError | None


class ArgumentsValidator(Protocol[CallArguments]):
    def __call__(self, arguments: CallArguments) -> PluginValidationError | None:
        ...


@dataclass(frozen=True, slots=True)
class ArgumentsConfig(Generic[CallArguments]):
    represent_as: type[CallArguments]
    # post parsing validators
    validators: Collection[ArgumentsValidator[CallArguments]] = ()


class TargetValidator(Protocol):
    def __call__(
        self, context_owner: CoreObjectDescriptor, context: VarsContextSection, raw_arguments: dict
    ) -> PluginValidationError | None:
        ...


@dataclass(frozen=True, slots=True)
class TargetConfig:
    """
    `Target` is an object for which plugin should be "performed".
    In most cases it will be object-owner of action.

    `detectors` contain callables that tries to extract targets ordered by priority
                (next in line won't be evaluated if previous returned non-empty result).
                They shouldn't contain any logic, only extraction.
                Sanity of evaluated targets should be checked either in `validators` or executor itself.
                If plugin is applied to context's owner, you can skip specifying detectors or set them to `()`
                and you'll get empty `targets` in plugin's `__call__`
                (it's expected you'll use `context_owner` in this case).

    `validators` are designed to be evaluated before `detectors`
                and check whether there are any conflicts specific to current plugin.
    """

    detectors: tuple[TargetDetector, ...] = ()
    # pre-detection validators
    validators: Collection[TargetValidator] = ()


class ContextValidator(Protocol):
    def __call__(
        self, context_owner: CoreObjectDescriptor, context: VarsContextSection
    ) -> PluginValidationError | None:
        ...


@dataclass(frozen=True, slots=True)
class ContextConfig:
    """
    It's a common situation that plugin is applied to context's owner
    or has some restrictions on what's the type of the owner might be.
    Use this config to provide universal validation for such requirements.
    Empty attributes are consider unspecified and no action will be taken based on them
    (e.g. empty `allow_only` won't check the type of owner).
    """

    allow_only: tuple[ADCMCoreType, ...] | frozenset[ADCMCoreType] = ()
    validators: Collection[ContextValidator] = ()


@dataclass(frozen=True, slots=True)
class PluginExecutorConfig(Generic[CallArguments]):
    arguments: ArgumentsConfig[CallArguments]
    target: TargetConfig = TargetConfig()
    context: ContextConfig = ContextConfig()


class ADCMAnsiblePluginExecutor(Generic[CallArguments, ReturnValue]):
    """
    Class to define operation associated with Ansible plugin without direct bounds to Ansible runtime.

    To create your own executor, you have to define configuration via `_config` and implement `__call__` method.
    Input validation and execution target detection will be performed according to the configuration.
    If input is valid and targets are detected, instance of executor will be called.

    Try to avoid overriding other methods whenever possible (and adequate).
    Override only when you find achieving your goals with configuration too tricky
    and `__call__` is "too late" for the things you require.
    """

    _config: PluginExecutorConfig[CallArguments]

    def __init__(self, arguments: dict, runtime_vars: dict):
        self._raw_arguments = arguments
        self._raw_vars = runtime_vars

    @abstractmethod
    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: CallArguments, runtime: RuntimeEnvironment
    ) -> CallResult[ReturnValue]:
        """
        Perform plugin operation.

        Mostly designed to call business functions based on parsed arguments and targets.
        Input sanity checks may be performed here if there's not enough information for them on previous steps.
        Examples of such checks are:
        - ensuring no duplicates in targets
        - checking for context owner - targets contradiction

        May raise exceptions, yet try to do so only in extraordinary cases.
        May access arguments (config, etc.) through `self`, but is generally discouraged.
        """
        message = f"{self.__class__} can't be called due to missing implementation"
        raise NotImplementedError(message)

    def execute(self) -> CallResult[ReturnValue]:
        """
        Process arguments and context based on configuration, then perform operation on processed data.
        Shouldn't raise errors.
        """

        try:
            call_arguments, ansible_vars = self._validate_inputs()
            call_context = ansible_vars.context
            owner_from_context = CoreObjectDescriptor(
                id=getattr(call_context, f"{call_context.type}_id"),
                type=ADCMCoreType(call_context.type) if call_context.type != "provider" else ADCMCoreType.HOSTPROVIDER,
            )
            self._validate_context(context_owner=owner_from_context, context=call_context)
            self._validate_targets(context_owner=owner_from_context, context=call_context)
            targets = self._detect_targets(
                context_owner=owner_from_context, context=call_context, parsed_arguments=call_arguments
            )
            result = self(
                targets=targets,
                arguments=call_arguments,
                runtime=RuntimeEnvironment(context_owner=owner_from_context, vars=ansible_vars),
            )
        except ADCMPluginError as err:
            return CallResult(value={}, changed=False, error=err)
        except Exception as err:  # noqa: BLE001
            message = "\n".join(
                (
                    f"Unhandled exception {err.__class__.__name__} occurred during {self.__class__.__name__} call.",
                    f"Message : {err}",
                    f"\n{traceback.format_exc()}",
                )
            )
            return CallResult(value={}, changed=False, error=PluginRuntimeError(message=message))

        return result

    def _validate_inputs(self) -> tuple[CallArguments, AnsibleRuntimeVars]:
        try:
            arguments = self._config.arguments.represent_as(**self._raw_arguments)
        except ValidationError as err:
            field_errors = compose_validation_error_details_message(err)
            message = f"Arguments doesn't match expected schema:\n{field_errors}"
            raise PluginValidationError(message=message) from err

        for validator in self._config.arguments.validators:
            error = validator(arguments)
            if error:
                raise error

        try:
            ansible_vars = AnsibleRuntimeVars(**self._raw_vars)
        except ValidationError as err:
            field_errors = compose_validation_error_details_message(err)
            message = f"Ansible variables doesn't match expected schema:\n{field_errors}"
            raise PluginValidationError(message=message) from err

        return arguments, ansible_vars

    def _validate_context(self, context_owner: CoreObjectDescriptor, context: VarsContextSection) -> None:
        allowed_context_owners = self._config.context.allow_only
        # it's important that if it's empty no check is performed
        if allowed_context_owners and context_owner.type not in allowed_context_owners:
            message = (
                "Plugin should be called only in context of "
                f"{' or '.join(sorted(owner.value for owner in allowed_context_owners))}, "
                f"not {context_owner.type.value}"
            )
            raise PluginContextError(message=message)

        for validator in self._config.context.validators:
            error = validator(context_owner=context_owner, context=context)
            if error:
                raise error

    def _validate_targets(self, context_owner: CoreObjectDescriptor, context: VarsContextSection) -> None:
        for validator in self._config.target.validators:
            error = validator(context_owner=context_owner, context=context, raw_arguments=self._raw_arguments)
            if error:
                raise error

    def _detect_targets(
        self,
        context_owner: CoreObjectDescriptor,
        context: VarsContextSection,
        parsed_arguments: BaseTypedArguments | BaseArgumentsWithTypedObjects,
    ) -> tuple[CoreObjectDescriptor, ...]:
        if not self._config.target.detectors:
            # Note that only in this case it's ok to return empty targets.
            # See `TargetConfig` and `ContextConfig` for more info.
            return ()

        for detector in self._config.target.detectors:
            result = detector(context_owner=context_owner, context=context, parsed_arguments=parsed_arguments)
            if result:
                return result

        message = "Failed to detect target from arguments of context"
        raise PluginTargetDetectionError(message)


class ADCMAnsiblePlugin(ActionBase):
    """
    Base class for custom `ActionModule`'s

    Descendants shouldn't contain logic defined directly in them.
    In most cases you'll just define in your module:

    ```
    class ActionModule(ADCMAnsiblePlugin):
        executor_class = PluginExecutorDescendantClass
    ```

    The only time you'll need to override `run` is when more ansible runtime context awareness is required.
    """

    TRANSFERS_FILES = False

    executor_class: type[ADCMAnsiblePluginExecutor]

    def run(self, tmp=None, task_vars=None):
        super().run(tmp=tmp, task_vars=task_vars)

        # Acquiring blocking lock on job's `config.json` file.
        #
        # Re-implemented from `job_lock` and similar functions,
        # skipping exception catching to avoid hiding actual errors under `AdcmEx`/`AnsibleActionFail` facade.
        # It looks like unpredicted situation, it should behave like one.
        #
        # Thou full motivation for performing such lock is unknown,
        # it looks like a way of preventing parallel execution of plugins(check out `flock` man for more info).
        # For example, parallel execution may be invoked when `run_once` isn't used in playbook
        # and target ansible host group isn't `localhost`.
        # It's also likely that such lock was somehow required for SQLite support,
        # when we can rely on transactions correctness using PostgreSQL.
        #
        # Ergo this behavior and its motivation should be revisioned, alternative solutions discovered.
        with (settings.RUN_DIR / str(task_vars["job"]["id"]) / "config.json").open(encoding="utf-8") as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)

            executor = self._get_executor(tmp=tmp, task_vars=task_vars)
            execution_result = executor.execute()

            if execution_result.error:
                raise AnsibleActionFail(message=to_native(execution_result.error.message)) from execution_result.error

        result_value = {}
        if isinstance(execution_result.value, Mapping):
            result_value |= execution_result.value
        elif execution_result.value is not None:
            result_value["value"] = execution_result.value

        return {"changed": execution_result.changed, **result_value}

    def _get_executor(self, tmp: Any, task_vars: Any) -> ADCMAnsiblePluginExecutor:
        _ = tmp
        return self.executor_class(arguments=self._task.args, runtime_vars=task_vars)
