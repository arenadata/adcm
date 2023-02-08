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

from functools import partial
from typing import Dict, Literal, Tuple, Union

import allure
import pytest
import requests
from adcm_client.objects import ADCMClient, Group, Policy, Role, User

from tests.functional.audit.conftest import (
    check_failed,
    check_succeed,
    make_auth_header,
)
from tests.functional.rbac.conftest import BusinessRoles as BR
from tests.library.audit.checkers import AuditLogChecker

# pylint: disable=redefined-outer-name


RBACObject = Union[User, Group, Role, Policy]
ChangeMethod = Literal["PUT", "PATCH"]


@pytest.fixture()
def rbac_objects(sdk_client_fs, rbac_create_data) -> Tuple[User, Group, Role, Policy]:
    """Create RBAC objects"""
    data_for_objects = {**rbac_create_data}
    # they are empty
    data_for_objects["policy"]["objects"] = data_for_objects["policy"].pop("object")
    data_for_objects["policy"]["user"] = [
        sdk_client_fs.user(id=u["id"]) for u in data_for_objects["policy"].pop("user")
    ]
    data_for_objects["policy"]["role"] = sdk_client_fs.role(id=data_for_objects["policy"].pop("role")["id"])
    return tuple(
        getattr(sdk_client_fs, f"{object_type}_create")(**data) for object_type, data in data_for_objects.items()
    )


@pytest.fixture()
def new_rbac_objects_info(sdk_client_fs) -> Dict[str, Dict[str, Dict]]:
    """Prepare "changes" for RBAC objects"""
    user = sdk_client_fs.user_create("justuser", "password")
    group = sdk_client_fs.group_create("justagroup")
    another_role: Role = sdk_client_fs.role(name=BR.VIEW_ROLES.value.role_name)
    return {
        "user": {
            "correct": {"first_name": "newfirstname", "group": [{"id": group.id}]},
            "incorrect": {"username": user.username},
        },
        "group": {
            "correct": {"description": "A whole new description", "user": [{"id": user.id}]},
            "incorrect": {"user": [{"id": 10000}]},
        },
        "role": {
            "correct": {"description": "Wow, such change", "child": [{"id": another_role.id}]},
            "incorrect": {"child": [{"id": -1}]},
        },
        "policy": {
            "correct": {"description": "Policy of Truth", "group": [{"id": group.id}]},
            "incorrect": {"role": {}},
        },
    }


@pytest.fixture()
def prepared_changes(sdk_client_fs, rbac_create_data, new_rbac_objects_info) -> dict:
    """
    Prepare dict with "object_changes"
    """
    client = sdk_client_fs
    initial = rbac_create_data

    def _get(key1, key2):
        return new_rbac_objects_info[key1]["correct"][key2]

    return {
        "user": {
            "previous": {"first_name": initial["user"]["first_name"], "group": []},
            "current": {
                "first_name": _get("user", "first_name"),
                "group": [f"{client.group(id=i['id']).name} [local]" for i in _get("user", "group")],
            },
        },
        "group": {
            "previous": {"description": initial["group"].get("description", ""), "user": []},
            "current": {
                "description": _get("group", "description"),
                "user": [client.user(id=i["id"]).username for i in _get("group", "user")],
            },
        },
        "role": {
            "previous": {
                "description": initial["role"]["description"],
                "child": [client.role(id=i["id"]).display_name for i in initial["role"]["child"]],
            },
            "current": {
                "description": _get("role", "description"),
                "child": [client.role(id=i["id"]).display_name for i in _get("role", "child")],
            },
        },
        "policy": {
            "previous": {"description": initial["policy"].get("description", ""), "group": []},
            "current": {
                "description": _get("policy", "description"),
                "group": [f"{client.group(id=i['id']).name} [local]" for i in _get("policy", "group")],
            },
        },
    }


@pytest.mark.parametrize("parse_with_context", ["update_rbac.yaml"], indirect=True)
@pytest.mark.parametrize("http_method", ["PATCH", "PUT"])
def test_update_rbac_objects(
    http_method: str,
    rbac_objects,
    new_rbac_objects_info,
    prepared_changes,
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
        check_succeed(change_as_admin(rbac_object=obj, data=new_info["correct"]))
        expected_code = 400 if not isinstance(obj, User) else 409
        check_failed(change_as_admin(rbac_object=obj, data=new_info["incorrect"]), exact_code=expected_code)
        check_failed(change_as_unauthorized(rbac_object=obj, data=new_info["incorrect"]), exact_code=403)
    checker = AuditLogChecker(parse_with_context({**rbac_create_data, "changes": {**prepared_changes}}))
    checker.set_user_map(sdk_client_fs)
    checker.check(sdk_client_fs.audit_operation_list())
    # return after https://tracker.yandex.ru/ADCM-3244
    # check_audit_cef_logs(client=sdk_client_fs, adcm_container=adcm_fs.container)


@pytest.mark.parametrize("parse_with_context", ["full_update_rbac.yaml"], indirect=True)
@pytest.mark.parametrize("http_method", ["PATCH", "PUT"])
def test_full_rbac_objects_update(http_method: str, parse_with_context, generic_provider, sdk_client_fs, rbac_objects):
    """
    Test on audit of full RBAC objects' update
    """
    user, group, role, policy = rbac_objects
    admin_creds = make_auth_header(sdk_client_fs)
    another_role: Role = sdk_client_fs.role(name=BR.VIEW_ROLES.value.role_name)
    new_role = sdk_client_fs.role_create(
        name="NewCustomRole",
        display_name="New Custom Role",
        description="Just a description",
        child=[{"id": sdk_client_fs.role(name=BR.VIEW_PROVIDER_CONFIGURATIONS.value.role_name).id}],
    )
    new_values = {
        "user": {
            "first_name": "BrandNewFirstName",
            "last_name": "BrandNewSecondName",
            "email": "brand@new.com",
            "is_superuser": True,
            "password": "whatsapassword",
            "profile": "what should be here",
            "group": [{"id": group.id}],
        },
        "group": {
            "name": "ChangedGroupName",
            "description": "Whole new description",
            "user": [{"id": sdk_client_fs.me().id}],
        },
        "role": {
            "display_name": "New Role Name",
            "description": "Whole new description",
            "child": [{"id": another_role.id}],
        },
        "policy": {
            "name": "NewPolicyName",
            "description": "Whole new description",
            "role": {"id": new_role.id},
            "object": [{"id": generic_provider.id, "name": generic_provider.name, "type": "provider"}],
            "user": [{"id": user.id}],
            "group": [{"id": group.id}],
        },
    }
    check_succeed(change_rbac_object(sdk_client_fs, user, http_method, new_values["user"], headers=admin_creds))
    check_succeed(change_rbac_object(sdk_client_fs, group, http_method, new_values["group"], headers=admin_creds))
    check_succeed(change_rbac_object(sdk_client_fs, role, http_method, new_values["role"], headers=admin_creds))
    check_succeed(change_rbac_object(sdk_client_fs, policy, http_method, new_values["policy"], headers=admin_creds))
    AuditLogChecker(parse_with_context({"provider": {"id": generic_provider.id, "name": generic_provider.name}})).check(
        sdk_client_fs.audit_operation_list()
    )


def change_rbac_object(
    client: ADCMClient, rbac_object: RBACObject, method: ChangeMethod, data: dict, **call_kwargs
) -> requests.Response:
    """
    Change RBAC object via API.
    If method is PUT, data is used to mutate current object's state
    """
    classname: str = rbac_object.__class__.__name__
    url = f"{client.url}/api/v1/rbac/{classname.lower()}/{rbac_object.id}/"
    prepared_body = data
    if method == "PUT":
        original_body: dict = requests.get(url, headers=make_auth_header(client)).json()
        prepared_body = {**original_body, **data}
    with allure.step(f"Changing {classname} object via {method} to {url} with data: {prepared_body}"):
        return getattr(requests, method.lower())(url, json=prepared_body, **call_kwargs)
