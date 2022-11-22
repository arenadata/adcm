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
# Generated by Django 3.2.7 on 2021-10-26 13:48

from typing import List

from adwp_base.errors import AdwpEx
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.db.transaction import atomic
from rest_framework import status

from cm.models import ADCMEntity
from rbac.models import Group, Policy, PolicyObject, Role, User
from rbac.utils import update_m2m_field


def _get_policy_object(obj: ADCMEntity) -> PolicyObject:
    """Get PolicyObject for ADCM entity"""
    content_type = ContentType.objects.get_for_model(obj)
    policy_object, _ = PolicyObject.objects.get_or_create(object_id=obj.id, content_type=content_type)
    return policy_object


def _check_subjects(users: List[User], groups: List[Group]) -> None:
    """Check if policy has at least one subject"""
    if not users and not groups:
        raise AdwpEx(
            'POLICY_INTEGRITY_ERROR',
            msg='Role should be bind with some users or groups',
            http_code=status.HTTP_400_BAD_REQUEST,
        )


def _check_objects(role: Role, objects: List[ADCMEntity]) -> None:
    """Check if objects are complies with role parametrization"""
    if role.parametrized_by_type:
        if not objects:
            raise AdwpEx(
                'POLICY_INTEGRITY_ERROR',
                msg='Parametrized role should be applied to some objects',
                http_code=status.HTTP_400_BAD_REQUEST,
            )
        for obj in objects:
            if obj.prototype.type not in role.parametrized_by_type:
                raise AdwpEx(
                    'POLICY_INTEGRITY_ERROR',
                    msg=(
                        f'Role parametrized  by {role.parametrized_by_type} '
                        f'could not be applied to {obj.prototype.type}'
                    ),
                    http_code=status.HTTP_400_BAD_REQUEST,
                )
    elif objects:
        raise AdwpEx(
            'POLICY_INTEGRITY_ERROR',
            msg='Not-parametrized role should not be applied to any objects',
            http_code=status.HTTP_400_BAD_REQUEST,
        )


@atomic
def policy_create(name: str, role: Role, built_in: bool = False, **kwargs):
    """
    Creating Policy object

    :param name: Policy name
    :type name: str
    :param role: Role
    :type role: Role
    :param built_in: Sing built in Policy
    :type built_in: bool
    :param kwargs: Other parameters for Policy object
    :type kwargs: dict
    :return: Policy
    :rtype: Policy
    """
    users = kwargs.get('user', [])
    groups = kwargs.get('group', [])
    _check_subjects(users, groups)

    objects = kwargs.get('object', [])
    _check_objects(role, objects)
    description = kwargs.get('description', '')

    try:
        policy = Policy.objects.create(name=name, role=role, built_in=built_in, description=description)
    except IntegrityError as exc:
        raise AdwpEx('POLICY_CREATE_ERROR', msg=f'Policy creation failed with error {exc}') from exc

    for obj in objects:
        policy.object.add(_get_policy_object(obj))

    policy.user.add(*users)
    policy.group.add(*groups)

    policy.apply()

    return policy


@atomic
def policy_update(policy: Policy, **kwargs) -> Policy:
    """
    Update Policy object

    :param policy: Policy object
    :type policy: Policy
    :param kwargs: parameters for Policy object
    :type kwargs: dict
    :return: Policy object
    :rtype: Policy
    """

    users = kwargs.get('user')
    groups = kwargs.get('group')
    _check_subjects(
        users if users is not None else policy.user.all(),
        groups if groups is not None else policy.group.all(),
    )

    role = kwargs.get('role')
    objects = kwargs.get('object')
    policy_old_objects = [po.object for po in policy.object.all()]
    _check_objects(role or policy.role, objects if objects is not None else policy_old_objects)
    if 'name' in kwargs:
        policy.name = kwargs['name']
    if 'description' in kwargs:
        policy.description = kwargs['description']
    if role is not None:
        policy.role = role
    if users is not None:
        update_m2m_field(policy.user, users)
    if groups is not None:
        update_m2m_field(policy.group, groups)
    if objects is not None:
        update_m2m_field(policy.object, [_get_policy_object(obj) for obj in objects])
    try:
        policy.save()
    except IntegrityError as exc:
        raise AdwpEx('POLICY_UPDATE_ERROR', msg=f'Policy update failed with error {exc}') from exc
    policy.apply()
    return policy
