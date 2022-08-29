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

"""Tests on audit logs for UPDATE of RBAC objects"""

# pylint: disable=redefined-outer-name

from functools import partial
from typing import Dict, Literal, Tuple, Union

import allure
import pytest
import requests
from adcm_client.objects import ADCMClient, Group, Policy, Role, User

from tests.functional.audit.conftest import check_failed, check_succeed, make_auth_header
from tests.functional.rbac.conftest import BusinessRoles as BR
from tests.library.audit.checkers import AuditLogChecker

RBACObject = Union[User, Group, Role, Policy]
ChangeMethod = Literal['PUT', 'PATCH']


@pytest.fixture()
def rbac_objects(sdk_client_fs, rbac_create_data) -> Tuple[User, Group, Role, Policy]:
    """Create RBAC objects"""
    data_for_objects = {**rbac_create_data}
    # they are empty
    data_for_objects['policy']['objects'] = data_for_objects['policy'].pop('object')
    data_for_objects['policy']['user'] = [
        sdk_client_fs.user(id=u['id']) for u in data_for_objects['policy'].pop('user')
    ]
    data_for_objects['policy']['role'] = sdk_client_fs.role(id=data_for_objects['policy'].pop('role')['id'])
    return tuple(
        getattr(sdk_client_fs, f'{object_type}_create')(**data) for object_type, data in data_for_objects.items()
    )


@pytest.fixture()
def new_rbac_objects_info(sdk_client_fs) -> Dict[str, Dict[str, Dict]]:
    """Prepare "changes" for RBAC objects"""
    user = sdk_client_fs.user_create('justuser', 'password')
    group = sdk_client_fs.group_create('justagroup')
    another_role: Role = sdk_client_fs.role(name=BR.ViewRoles.value.role_name)
    return {
        'user': {
            'correct': {'first_name': 'newfirstname', 'group': [{'id': group.id}]},
            'incorrect': {'username': user.username},
        },
        'group': {
            'correct': {'description': 'A whole new description', 'user': [{'id': user.id}]},
            'incorrect': {'user': [{'id': 10000}]},
        },
        'role': {
            'correct': {'description': 'Wow, such change', 'child': [{'id': another_role.id}]},
            'incorrect': {'child': [{'id': -1}]},
        },
        'policy': {
            'correct': {'description': 'Policy of Truth', 'group': [{'id': group.id}]},
            'incorrect': {'role': {}},
        },
    }


@pytest.mark.parametrize('parse_with_context', ['update_rbac.yaml'], indirect=True)
@pytest.mark.parametrize('http_method', ['PATCH', 'PUT'])  # pylint: disable-next=too-many-arguments
def test_update_rbac_objects(
    http_method: str,
    rbac_objects,
    new_rbac_objects_info,
    parse_with_context,
    rbac_create_data,
    sdk_client_fs,
    unauthorized_creds,
):
    """Test update (success, fail, denied) of RBAC objects: user, group, role, policy"""
    admin_creds = make_auth_header(sdk_client_fs)
    change_as_admin = partial(change_rbac_object, sdk_client_fs, method=http_method, headers=admin_creds)
    change_as_unauthorized = partial(change_rbac_object, sdk_client_fs, method=http_method, headers=unauthorized_creds)

    for obj in rbac_objects:
        new_info = {**new_rbac_objects_info[obj.__class__.__name__.lower()]}
        check_succeed(change_as_admin(rbac_object=obj, data=new_info['correct']))
        check_failed(change_as_admin(rbac_object=obj, data=new_info['incorrect']), exact_code=400)
        check_failed(change_as_unauthorized(rbac_object=obj, data=new_info['incorrect']), exact_code=403)
    checker = AuditLogChecker(parse_with_context(rbac_create_data))
    checker.set_user_map(sdk_client_fs)
    checker.check(sdk_client_fs.audit_operation_list())


def change_rbac_object(
    client: ADCMClient, rbac_object: RBACObject, method: ChangeMethod, data: dict, **call_kwargs
) -> requests.Response:
    """
    Change RBAC object via API.
    If method is PUT, data is used to mutate current object's state
    """
    classname: str = rbac_object.__class__.__name__
    url = f'{client.url}/api/v1/rbac/{classname.lower()}/{rbac_object.id}/'
    prepared_body = data
    if method == 'PUT':
        original_body: dict = requests.get(url, headers=make_auth_header(client)).json()
        prepared_body = {**original_body, **data}
    with allure.step(f'Changing {classname} object via {method} to {url} with data: {prepared_body}'):
        return getattr(requests, method.lower())(url, json=prepared_body, **call_kwargs)