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

from dataclasses import dataclass, fields
from typing import Optional, Dict, Union, NamedTuple, Collection, List

from adcm_client.audit import OperationType, AuditOperation, OperationResult, ObjectType


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

_NAMED_OPERATIONS: Dict[str, NamedOperation] = {
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
    )
}


@dataclass(frozen=True)  # pylint:disable-next=too-many-instance-attributes
class Operation:
    """
    Information about audited operation.
    Should be used mostly to compare API operation objects with it.
    """

    object_type: ObjectType
    object_name: str

    operation_type: OperationType
    operation_name: str
    operation_result: OperationResult

    username: str
    user_id: int

    object_changes: Optional[Dict[str, dict]] = None

    def is_equal_to(self, operation_object: AuditOperation) -> bool:
        """Compare this operation to an API audit operation object"""
        for field_name in (f.name for f in fields(self) if f != 'username'):
            if getattr(self, field_name) != getattr(operation_object, field_name):
                return False
        return True


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
                object_type=object_type,
                object_name=object_['name'],
                operation_result=result,
                operation_type=operation_type,
                operation_name=_detect_operation_name(object_type, operation_type, operation_info),
                username=username,
                user_id=username_id_map[username],
            )
        )
    return operations


def is_name_of_object_type(name: str) -> bool:
    """Check if name is one of `OperationType` names"""
    for type_ in OperationType:
        if name == type_.value:
            return True
    return False


def _detect_operation_name(object_type: ObjectType, operation_type: OperationType, operation_info: dict) -> str:
    if object_type in _create_delete_types and operation_type in (OperationType.CREATE, OperationType.DELETE):
        return f'{object_type.value.capitalize()} {operation_type.value.lower()}d'

    how = _unwrap_how(operation_info.get('how', {}))
    if not how or 'operation' not in how:
        raise KeyError(
            'There should be "how" section specifying operation for audit record described as\n'
            f'"{operation_type.value} {object_type.value}: {operation_info}"'
        )

    named_operation = _NAMED_OPERATIONS.get(how['operation'], None)
    if not named_operation:
        raise KeyError(
            f'Incorrect operation name: {how["operation"]}.\n'
            'If operation name is correct, add it to `_NAMED_OPERATIONS`\n'
            f'Registered names: {", ".join(_NAMED_OPERATIONS.keys())}\n'
        )

    return named_operation.resolve(object_type, **how)


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
