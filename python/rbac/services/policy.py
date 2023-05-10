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
from cm.models import ADCMEntity
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.db.transaction import atomic
from rbac.models import Policy, PolicyObject, Role


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
def policy_create(name: str, role: Role, built_in: bool = False, **kwargs) -> Policy | None:
    users = kwargs.get("user", [])
    groups = kwargs.get("group", [])
    if not users and not groups:
        raise_adcm_ex(
            "POLICY_INTEGRITY_ERROR",
            msg="Role should be bind with some users or groups",
        )

    objects = kwargs.get("object", [])
    _check_objects(role, objects)
    description = kwargs.get("description", "")

    try:
        policy = Policy.objects.create(name=name, role=role, built_in=built_in, description=description)
        for obj in objects:
            content_type = ContentType.objects.get_for_model(obj)
            policy_object, _ = PolicyObject.objects.get_or_create(object_id=obj.id, content_type=content_type)
            policy.object.add(policy_object)

        policy.user.add(*users)
        policy.group.add(*groups)

        policy.apply()

        return policy
    except IntegrityError as e:
        raise_adcm_ex("POLICY_CREATE_ERROR", msg=f"Policy creation failed with error {e}")

    return None


@atomic
def policy_update(policy: Policy, **kwargs) -> Policy:
    users = kwargs.get("user")
    groups = kwargs.get("group")
    if not (users or policy.user.all()) and not (groups or policy.group.all()):
        raise_adcm_ex(
            "POLICY_INTEGRITY_ERROR",
            msg="Role should be bind with some users or groups",
        )

    role = kwargs.get("role")
    objects = kwargs.get("object")
    policy_old_objects = [po.object for po in policy.object.all()]
    _check_objects(role or policy.role, objects if objects is not None else policy_old_objects)

    if "name" in kwargs:
        policy.name = kwargs["name"]

    if "description" in kwargs:
        policy.description = kwargs["description"]

    if role is not None:
        policy.role = role

    if users is not None:
        policy.user.clear()
        policy.user.add(*users)

    if groups is not None:
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
