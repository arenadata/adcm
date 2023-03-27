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

"""Defines basic entities like Operation and NamedOperation to work with audit log scenarios"""

from collections.abc import Collection
from dataclasses import dataclass, field, fields
from typing import ClassVar, Literal, NamedTuple

from adcm_client.audit import AuditOperation, ObjectType, OperationResult, OperationType

# types that can just be "created" and "deleted
_create_delete_types = (
    ObjectType.CLUSTER,
    ObjectType.PROVIDER,
    ObjectType.HOST,
    ObjectType.USER,
    ObjectType.GROUP,
    ObjectType.POLICY,
    ObjectType.ROLE,
)

# types that are just "updated"
_simple_update_types = (
    ObjectType.USER,
    ObjectType.GROUP,
    ObjectType.POLICY,
    ObjectType.ROLE,
)


class NamedOperation(NamedTuple):
    """Operation with specific name (not just created/deleted)"""

    name: str
    naming_template: str
    allowed_types: Collection[ObjectType]

    def resolve(self, object_type: ObjectType, **format_args) -> str:
        """Create `operation_name` from template string based on type and parameters (from "how" section)"""
        if object_type not in self.allowed_types:
            raise ValueError(
                f"Operation {self.name} can not be performed on {object_type}.\n"
                "Please check definition of an operation.",
            )
        try:
            type_ = object_type.value.capitalize() if object_type != ObjectType.ADCM else object_type.value.upper()
            return self.naming_template.format(type_=type_, **format_args).strip()
        except KeyError as e:
            raise KeyError(
                f'It looks like you missed some keys required to format "{self.naming_template}" string\n'
                'Most likely you should add those keys to audit log operation "how" section\n'
                f"Original error: {e}",
            ) from e


_OBJECTS_WITH_CONFIG_GROUPS = (ObjectType.CLUSTER, ObjectType.SERVICE, ObjectType.COMPONENT)
_OBJECTS_WITH_ACTIONS_AND_CONFIGS = (
    ObjectType.ADCM,
    ObjectType.CLUSTER,
    ObjectType.SERVICE,
    ObjectType.COMPONENT,
    ObjectType.PROVIDER,
    ObjectType.HOST,
)

_NAMED_OPERATIONS: dict[str | tuple[OperationResult, str], NamedOperation] = {
    named_operation.name: named_operation
    for named_operation in (
        # bundle
        NamedOperation("load", "Bundle loaded", (ObjectType.BUNDLE,)),
        NamedOperation("upload", "Bundle uploaded", (ObjectType.BUNDLE,)),
        NamedOperation("accept-license", "Bundle license accepted", (ObjectType.BUNDLE,)),
        NamedOperation("change-description", "Bundle updated", (ObjectType.BUNDLE,)),
        # cluster
        NamedOperation("add-service", "{name} service added", (ObjectType.CLUSTER,)),
        NamedOperation("remove-service", "{name} service removed", (ObjectType.CLUSTER,)),
        # there should be an object cleanup for this case
        NamedOperation("remove-not-existing-service", "service removed", (ObjectType.CLUSTER,)),
        NamedOperation("add-host", "{name} host added", (ObjectType.CLUSTER,)),
        NamedOperation("remove-host", "{name} host removed", (ObjectType.CLUSTER,)),
        NamedOperation("set-hostcomponent", "Host-Component map updated", (ObjectType.CLUSTER,)),
        # configs
        NamedOperation(
            "set-config",  # restore is the same
            "{type_} configuration updated",
            _OBJECTS_WITH_ACTIONS_AND_CONFIGS,
        ),
        # RBAC and "renamable" objects
        NamedOperation(
            "change-properties",
            "{type_} updated",
            (
                ObjectType.USER,
                ObjectType.GROUP,
                ObjectType.ROLE,
                ObjectType.POLICY,
                ObjectType.CLUSTER,
                ObjectType.SERVICE,
                ObjectType.COMPONENT,
                ObjectType.HOST,
            ),
        ),
        # Imports / Binds
        NamedOperation("change-imports", "{type_} import updated", (ObjectType.CLUSTER, ObjectType.SERVICE)),
        # ! note that name in (un-)bind operations is like "<Export cluster name>/<Export service display name>"
        NamedOperation("bind", "{type_} bound to {name}", (ObjectType.CLUSTER, ObjectType.SERVICE)),
        NamedOperation("unbind", "{name} unbound", (ObjectType.CLUSTER, ObjectType.SERVICE)),
        # Actions
        NamedOperation("launch-action", "{name} action launched", _OBJECTS_WITH_ACTIONS_AND_CONFIGS),
        NamedOperation("complete-action", "{name} action completed", _OBJECTS_WITH_ACTIONS_AND_CONFIGS),
        # Tasks
        NamedOperation("cancel-task", "{name} cancelled", _OBJECTS_WITH_ACTIONS_AND_CONFIGS),
        NamedOperation("restart-task", "{name} restarted", _OBJECTS_WITH_ACTIONS_AND_CONFIGS),
        # object will be nullified
        NamedOperation("restart-not-existing-task", "{name} restarted", _OBJECTS_WITH_ACTIONS_AND_CONFIGS),
        # Background tasks
        NamedOperation("launch-background-task", '"{name}" job launched', (ObjectType.ADCM,)),
        NamedOperation("complete-background-task", '"{name}" job completed', (ObjectType.ADCM,)),
        # Group config
        NamedOperation(
            "add-host-to-group-config",
            "{host} host added to {name} configuration group",
            _OBJECTS_WITH_CONFIG_GROUPS,
        ),
        NamedOperation(
            "remove-host-from-group-config",
            "{host} host removed from {name} configuration group",
            _OBJECTS_WITH_CONFIG_GROUPS,
        ),
        NamedOperation(
            "update-group-config",
            "{name} configuration group updated",
            _OBJECTS_WITH_CONFIG_GROUPS,
        ),
        NamedOperation(
            "delete-group-config",
            "{name} configuration group deleted",
            _OBJECTS_WITH_CONFIG_GROUPS,
        ),
        # Upgrades
        NamedOperation("do-upgrade", "Upgraded to {name}", (ObjectType.CLUSTER, ObjectType.PROVIDER)),
        NamedOperation("launch-upgrade", "{name} upgrade launched", (ObjectType.CLUSTER, ObjectType.PROVIDER)),
        NamedOperation(
            "complete-upgrade",
            "{name} upgrade completed",
            (ObjectType.CLUSTER, ObjectType.PROVIDER),
        ),
    )
}

_failed_denied_config_group_creation = NamedOperation(
    "create-group-config",
    "configuration group created",
    (ObjectType.CLUSTER, ObjectType.SERVICE, ObjectType.COMPONENT),
)
_NAMED_OPERATIONS.update(
    {
        # Group config
        (OperationResult.SUCCESS, "create-group-config"): NamedOperation(
            "create-group-config",
            "{name} configuration group created",
            (ObjectType.CLUSTER, ObjectType.SERVICE, ObjectType.COMPONENT),
        ),
        (OperationResult.FAIL, "create-group-config"): _failed_denied_config_group_creation,
        (OperationResult.DENIED, "create-group-config"): _failed_denied_config_group_creation,
    },
)


@dataclass()  # pylint:disable-next=too-many-instance-attributes
class Operation:
    """
    Information about audited operation.
    Should be used mostly to compare API operation objects with it.
    """

    EXCLUDED_FROM_COMPARISON: ClassVar = ("username", "code")

    # main info
    user_id: int | None
    operation_type: OperationType
    operation_name: str = field(init=False)
    operation_result: OperationResult
    object_changes: dict[str, dict]

    # may be or may not be based on operation type and result
    # but they should be passed directly, because it's an important part of the logic

    object_type: ObjectType | None
    object_name: str | None

    # not from API, but suitable for displaying what was expected
    username: str | None = field(default=None, compare=False)

    # used for operation name building
    # the value from "how" section of operation description in scenario
    code: dict[Literal["operation", "name"], str] = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self):
        self.operation_name = self._detect_operation_name()
        self._nullify_object()
        self._nullify_user()

    def is_equal_to(self, operation_object: AuditOperation) -> bool:
        """Compare this operation to an API audit operation object"""
        for field_name in (f.name for f in fields(self) if f.name not in self.EXCLUDED_FROM_COMPARISON):
            if getattr(self, field_name) != getattr(operation_object, field_name):
                return False
        return True

    def _detect_operation_name(self) -> str:
        """Detect the operation name"""
        # creation of part (like group-config) is top priority
        if (
            self.object_type in _create_delete_types
            and self.operation_type
            in (
                OperationType.CREATE,
                OperationType.DELETE,
            )
            and not self.code
        ):
            # code may be important for stuff like group config creation
            return f"{self.object_type.value.capitalize()} {self.operation_type.value.lower()}d"

        if self.object_type in _simple_update_types and self.operation_type == OperationType.UPDATE:
            return f"{self.object_type.value.capitalize()} updated"

        # special case, no need for "how" section here, I think
        if self.object_type == ObjectType.BUNDLE and self.operation_type == OperationType.DELETE:
            return "Bundle deleted"

        if not self.code or "operation" not in self.code:
            raise KeyError(
                'There should be "how" section specifying operation for audit record described as\n'
                f'"{self.operation_type.value} {self.object_type.value} {self.object_name}"',
            )

        operation = self.code["operation"]
        named_operation = _NAMED_OPERATIONS.get(operation, None)
        if named_operation is None:
            named_operation = _NAMED_OPERATIONS.get((self.operation_result, operation), None)
        if not named_operation:
            raise KeyError(
                f"Incorrect operation name: {operation}.\n"
                "If operation name is correct, add it to `_NAMED_OPERATIONS`\n"
                "Registered names: "
                ", ".join(k if isinstance(k, str) else str(k) for k in _NAMED_OPERATIONS.keys()),
            )

        return named_operation.resolve(self.object_type, **self.code)

    def _nullify_object(self) -> None:
        """
        There are cases when object type is required for building operation name,
        but will not be presented in operation object (audit object reference == None).
        This function sets object-related fields to None based on the case.
        """
        if (
            (
                self.operation_type == OperationType.CREATE
                and self.operation_result in (OperationResult.FAIL, OperationResult.DENIED)
            )
            # some operations don't have object, like Bundle upload,
            # because no ADCM object is created on this operation
            or (self.operation_name == _NAMED_OPERATIONS["upload"].naming_template)
            or (
                self.code.get("operation")
                in {
                    "launch-background-task",
                    "complete-background-task",
                    "remove-not-existing-service",
                    "restart-not-existing-task",
                }
            )
        ):
            self.object_type = None
            self.object_name = None

    def _nullify_user(self) -> None:
        """
        There are cases when there will be no user (e.g. finishing actions),
        so it's easier to change all of them in one place rather than always set it in audit scenario.
        Bad thing is that this replacement is not obvious for the audit scenario writer,
        but I find this the cheaper and cleaner way, because there are too few cases for that:
        making it clearly "None" in scenario will make us "consider" nullable users in both parser and converter.
        """
        if self.operation_type == OperationType.UPDATE and (
            self.code.get("operation") in {"complete-action", "complete-upgrade"}
        ):
            self.user_id = None
            self.username = None


def convert_to_operations(
    raw_operations: list[dict],
    default_username: str,
    default_result: str,
    username_id_map: dict[str, int],
) -> list[Operation]:
    """Convert parsed from file audit operations to Operation objects"""
    required_users = {
        default_username,
        *[op["username"] for op in raw_operations if "username" in op],
    }
    _check_all_users_are_presented(required_users, username_id_map)
    operations = []
    for data in raw_operations:
        operation_data = {**data}
        username = operation_data.pop("username", default_username)
        result = OperationResult(operation_data.pop("result", default_result))
        # there should be at least one
        type_ = next(filter(is_name_of_operation_type, data.keys()))
        operation_info = data[type_]
        operation_type = OperationType(type_)
        object_ = operation_info["what"]
        object_type = ObjectType(object_["type"])
        operations.append(
            Operation(
                user_id=username_id_map[username],
                operation_type=operation_type,
                operation_result=result,
                object_changes=operation_info.get("changes", {}),
                object_type=object_type,
                object_name=object_.get("name", None),
                username=username,
                code=_unwrap_how(operation_info.get("how", {})),
            ),
        )
    return operations


def is_name_of_operation_type(name: str) -> bool:
    """Check if name is one of `OperationType` names"""
    for type_ in OperationType:
        if name == type_.value:
            return True
    return False


def _check_all_users_are_presented(usernames, username_id_map):
    registered_users = set(username_id_map.keys())
    if registered_users.issuperset(usernames):
        return
    raise RuntimeError(
        "Not all users are presented in users map, so their ids cannot be figured out from username.\n",
        "You should try to use `set_user_map` method.\n" f"Missing usernames: {usernames.difference(registered_users)}",
    )


def _unwrap_how(how: dict | str) -> dict:
    if isinstance(how, dict):
        return how
    return {"operation": how}
