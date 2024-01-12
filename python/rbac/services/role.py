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

from cm.errors import raise_adcm_ex
from django.db import IntegrityError
from django.db.transaction import atomic
from rest_framework.exceptions import ValidationError

from rbac.models import Role, RoleTypes


def check_role_child(child: list[Role], partial=False):
    param_set = set()
    cluster_hierarchy = {"cluster", "service", "component"}
    provider_hierarchy = {"provider"}

    if not child and not partial:
        errors = {"child": ["Roles without children make not sense"]}

        raise ValidationError(errors)

    for item in child:
        if not item.built_in:
            errors = {"child": ["Only built-in roles allowed to be included as children."]}

            raise ValidationError(errors)

        if item.type != RoleTypes.BUSINESS:
            errors = {"child": ["Only business roles allowed to be included as children."]}

            raise ValidationError(errors)

        param_set.update(item.parametrized_by_type)
        if param_set.intersection(provider_hierarchy) and param_set.intersection(cluster_hierarchy):
            raise_adcm_ex("ROLE_CONFLICT")

    return list(param_set)


@atomic
def role_create(built_in=False, type_of_role=RoleTypes.ROLE, **kwargs) -> Role | None:
    child = kwargs.pop("child", [])
    parametrized_by = check_role_child(child)
    name = kwargs.pop("name", "")
    if name == "":
        name = kwargs["display_name"]

    try:
        role = Role.objects.create(
            name=name,
            built_in=built_in,
            type=type_of_role,
            module_name="rbac.roles",
            class_name="ParentRole",
            parametrized_by_type=parametrized_by,
            **kwargs,
        )
        role.child.add(*child)

        return role  # noqa: TRY300
    except IntegrityError:
        raise_adcm_ex("ROLE_CREATE_ERROR")

    return None


@atomic
def role_update(role: Role, partial, **kwargs) -> Role:
    child = kwargs.pop("child", [])
    parametrized_by = check_role_child(child, partial)
    kwargs["parametrized_by_type"] = parametrized_by
    kwargs.pop("name", None)
    for key, value in kwargs.items():
        setattr(role, key, value)

    try:
        role.save()
    except IntegrityError as e:
        raise_adcm_ex("ROLE_UPDATE_ERROR", msg=f"Role update failed with error {e}")

    if child:
        role.child.clear()
        role.child.add(*child)

    for policy in role.policy_set.order_by("id"):
        policy.apply()

    return role
