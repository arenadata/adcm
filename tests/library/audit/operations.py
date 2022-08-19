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

from dataclasses import dataclass, field, fields
from typing import ClassVar, Collection, Dict, List, Literal, NamedTuple, Optional, Tuple, Union

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


class NamedOperation(NamedTuple):
    """Operation with specific name (not just created/deleted)"""

    name: str
    naming_template: str
    allowed_types: Collection[ObjectType]

    def resolve(self, object_type: ObjectType, **format_args) -> str:
        """Create `operation_name` from template string based on type and parameters (from "how" section)"""
        if object_type not in self.allowed_types:
            raise ValueError(
                f'Operation {self.name} can not be performed on {object_type}.\n'
                'Please check definition of an operation.'
            )
        try:
            return self.naming_template.format(type_=object_type.value.capitalize(), **format_args)
        except KeyError as e:
            raise KeyError(
                f'It looks like you missed some keys required to format "{self.naming_template}" string\n'
                'Most likely you should add those keys to audit log operation "how" section\n'
                f'Original error: {e}'
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

_NAMED_OPERATIONS: Dict[Union[str, Tuple[OperationResult, str]], NamedOperation] = {
    named_operation.name: named_operation
    for named_operation in (
        # bundle
        NamedOperation('load', 'Bundle loaded', (ObjectType.BUNDLE,)),
        NamedOperation('upload', 'Bundle uploaded', (ObjectType.BUNDLE,)),
        NamedOperation('accept-license', 'Bundle license accepted', (ObjectType.BUNDLE,)),
        NamedOperation('change-description', 'Bundle updated', (ObjectType.BUNDLE,)),
        # cluster
        NamedOperation('add-service', '{name} service added', (ObjectType.CLUSTER,)),
        NamedOperation('delete-service', '{name} service deleted', (ObjectType.CLUSTER,)),
        NamedOperation('add-host', '{name} host added', (ObjectType.CLUSTER,)),
        NamedOperation('remove-host', '{name} host removed', (ObjectType.CLUSTER,)),
        NamedOperation('set-hostcomponent', 'Host-component map updated', (ObjectType.CLUSTER,)),
        # configs
        NamedOperation(
            'set-config',
            '{type_} configuration updated',
            _OBJECTS_WITH_ACTIONS_AND_CONFIGS,
        ),
        # group configs
        NamedOperation(
            'add-host-to-gc',
            '{name} host added to {group_name} configuration group',
            _OBJECTS_WITH_CONFIG_GROUPS,
        ),
        NamedOperation(
            'remove-host-from-gc',
            '{name} host removed from {group_name} configuration group',
            _OBJECTS_WITH_CONFIG_GROUPS,
        ),
        NamedOperation('delete-cg', '{group_name} configuration group deleted', _OBJECTS_WITH_CONFIG_GROUPS),
        # RBAC
        NamedOperation(
            'change-properties',
            '{type_} updated',
            (ObjectType.USER, ObjectType.GROUP, ObjectType.ROLE, ObjectType.POLICY),
        ),
        # Actions
        NamedOperation('launch-action', '{name} action launched', _OBJECTS_WITH_ACTIONS_AND_CONFIGS),
        NamedOperation('complete-action', '{name} action completed', _OBJECTS_WITH_ACTIONS_AND_CONFIGS),
        # Group config
        NamedOperation(
            'delete-group-config',
            '{name} configuration group deleted',
            (ObjectType.CLUSTER, ObjectType.SERVICE, ObjectType.COMPONENT),
        ),
    )
}

_failed_denied_config_group_creation = NamedOperation(
    'create-group-config',
    'configuration group created',
    (ObjectType.CLUSTER, ObjectType.SERVICE, ObjectType.COMPONENT),
)
_NAMED_OPERATIONS.update(
    {
        # Group config
        (OperationResult.SUCCESS, 'create-group-config'): NamedOperation(
            'create-group-config',
            '{name} configuration group created',
            (ObjectType.CLUSTER, ObjectType.SERVICE, ObjectType.COMPONENT),
        ),
        (OperationResult.FAIL, 'create-group-config'): _failed_denied_config_group_creation,
        (OperationResult.DENIED, 'create-group-config'): _failed_denied_config_group_creation,
    }
)


@dataclass()  # pylint:disable-next=too-many-instance-attributes
class Operation:
    """
    Information about audited operation.
    Should be used mostly to compare API operation objects with it.
    """

    EXCLUDED_FROM_COMPARISON: ClassVar = ('username', 'code')

    # main info
    user_id: int
    operation_type: OperationType
    operation_name: str = field(init=False)
    operation_result: OperationResult
    # TODO check if it's the final decision
    object_changes: Dict[str, dict]
    # may be or may not be based on operation type and result
    # but they should be passed directly, because it's an important part of the logic
    object_type: Optional[ObjectType]
    object_name: Optional[str]
    # not from API, but suitable for displaying what was expected
    username: Optional[str] = field(default=None, compare=False)
    # used for operation name building
    # the value from "how" section of operation description in scenario
    code: Dict[Literal['operation', 'name'], str] = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self):
        self.operation_name = self._detect_operation_name()
        self._nullify_object()

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
            return f'{self.object_type.value.capitalize()} {self.operation_type.value.lower()}d'

        # special case, no need for "how" section here, I think
        if self.object_type == ObjectType.BUNDLE and self.operation_type == OperationType.DELETE:
            return 'Bundle deleted'

        if not self.code or 'operation' not in self.code:
            raise KeyError(
                'There should be "how" section specifying operation for audit record described as\n'
                f'"{self.operation_type.value} {self.object_type.value} {self.object_name}"'
            )

        operation = self.code['operation']
        named_operation = _NAMED_OPERATIONS.get(operation, None)
        if named_operation is None:
            named_operation = _NAMED_OPERATIONS.get((self.operation_result, operation), None)
        if not named_operation:
            raise KeyError(
                f'Incorrect operation name: {operation}.\n'
                'If operation name is correct, add it to `_NAMED_OPERATIONS`\n'
                'Registered names: '
                ", ".join(k if isinstance(k, str) else str(k) for k in _NAMED_OPERATIONS.keys())
            )

        return named_operation.resolve(self.object_type, **self.code)

    def _nullify_object(self) -> None:
        """
        There are cases when object type is required for building operation name,
        but will not be presented in operation object (audit object reference == None).
        This funciton sets object-related fields to None based on the case.
        """
        if (
            (
                self.operation_type == OperationType.CREATE
                and self.operation_result in (OperationResult.FAIL, OperationResult.DENIED)
            )
            # some operations don't have object, like Bundle upload,
            # because no ADCM object is created on this operation
            or (self.operation_name == _NAMED_OPERATIONS['upload'].naming_template)
        ):
            self.object_type = None
            self.object_name = None


def convert_to_operations(
    raw_operations: List[dict], default_username: str, default_result: str, username_id_map: Dict[str, int]
) -> List[Operation]:
    """Convert parsed from file audit operations to Operation objects"""
    required_users = {default_username, *[op['username'] for op in raw_operations if 'username' in op]}
    _check_all_users_are_presented(required_users, username_id_map)
    operations = []
    for data in raw_operations:
        operation_data = {**data}
        username = operation_data.pop('username', default_username)
        result = OperationResult(operation_data.pop('result', default_result))
        # there should be at least one
        type_ = next(filter(is_name_of_object_type, data.keys()))
        operation_info = data[type_]
        operation_type = OperationType(type_)
        object_ = operation_info['what']
        object_type = ObjectType(object_['type'])
        operations.append(
            Operation(
                user_id=username_id_map[username],
                operation_type=operation_type,
                operation_result=result,
                # TODO implement object_changes passing in scenario
                object_changes={},
                object_type=object_type,
                object_name=object_.get('name', None),
                username=username,
                code=_unwrap_how(operation_info.get('how', {})),
            )
        )
    return operations


def is_name_of_object_type(name: str) -> bool:
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
        'Not all users are presented in users map, so their ids cannot be figured out from username.\n',
        'You should try to use `set_user_map` method.\n' f'Missing usernames: {usernames.difference(registered_users)}',
    )


def _unwrap_how(how: Union[dict, str]) -> dict:
    if isinstance(how, dict):
        return how
    return {'operation': how}