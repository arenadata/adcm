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
from typing import Tuple

from cm.errors import raise_adcm_ex
from cm.models import ADCMEntity
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.db.transaction import atomic
from rbac.models import Group, Policy, PolicyObject, Role


def _extract_policy_objects(**kwargs) -> Tuple[Role, list, list]:
    role = kwargs.get("role", None)
    if "v2" in kwargs:
        groupd_ids = kwargs.get("group", [])
        objects_ids = kwargs.get("object", [])
        role_id = role["id"]
        groups = Group.objects.filter(id__in=[g["id"] for g in groupd_ids])
        objects = PolicyObject.objects.filter(id__in=[g["id"] for g in objects_ids])
        role = Role.objects.filter(id=role_id).last()
    else:
        groups = kwargs.get("group", [])
        objects = kwargs.get("object", [])
    return role, groups, objects


def _check_objects(role: Role, objects: list[ADCMEntity]) -> None:
    if role.parametrized_by_type:
        if not objects:
            raise_adcm_ex(
                "POLICY_INTEGRITY_ERROR",
                msg="Parametrized role should be applied to some objects",
            )

        for obj in objects:
            if obj.prototype.type not in role.parametrized_by_type:
                raise_adcm_ex(
                    "POLICY_INTEGRITY_ERROR",
                    msg=(
                        f"Role parametrized  by {role.parametrized_by_type} "
                        f"could not be applied to {obj.prototype.type}"
                    ),
                )
    elif objects:
        raise_adcm_ex(
            "POLICY_INTEGRITY_ERROR",
            msg="Not-parametrized role should not be applied to any objects",
        )


@atomic
def policy_create(name: str, role: Role | dict, built_in: bool = False, **kwargs) -> Policy | None:
    kwargs["role"] = role
    role, groups, objects = _extract_policy_objects(**kwargs)

    if not groups:
        raise_adcm_ex(
            "POLICY_INTEGRITY_ERROR",
            msg="Policy should contain at least one group",
        )

    _check_objects(role, objects)
    description = kwargs.get("description", "")

    try:
        policy = Policy.objects.create(name=name, role=role, built_in=built_in, description=description)
        for obj in objects:
            content_type = ContentType.objects.get_for_model(obj)
            policy_object, _ = PolicyObject.objects.get_or_create(object_id=obj.id, content_type=content_type)
            policy.object.add(policy_object)

        policy.group.add(*groups)

        policy.apply()

        return policy
    except IntegrityError as e:
        raise_adcm_ex("POLICY_CREATE_ERROR", msg=f"Policy creation failed with error {e}")

    return None


@atomic
def policy_update(policy: Policy, **kwargs) -> Policy:
    role, groups, objects = _extract_policy_objects(**kwargs)
    if groups != [] and not groups:
        raise_adcm_ex(
            "POLICY_INTEGRITY_ERROR",
            msg="Policy should contain at least one group",
        )

    policy_old_objects = [po.object for po in policy.object.all()]
    _check_objects(role or policy.role, objects if objects is not None else policy_old_objects)

    if "name" in kwargs:
        policy.name = kwargs["name"]

    if "description" in kwargs:
        policy.description = kwargs["description"]

    if role is not None:
        policy.role = role

    if groups:
        policy.group.clear()
        policy.group.add(*groups)

    if objects is not None:
        policy.object.clear()

        policy_objects = []
        for obj in objects:
            content_type = ContentType.objects.get_for_model(obj)
            policy_object, _ = PolicyObject.objects.get_or_create(object_id=obj.id, content_type=content_type)
            policy_objects.append(policy_object)

        policy.object.add(*policy_objects)

    try:
        policy.save()
    except IntegrityError as e:
        raise_adcm_ex("POLICY_UPDATE_ERROR", msg=f"Policy update failed with error {e}")

    policy.apply()

    return policy
