# pylint: disable=too-many-lines,unsupported-membership-test,unsupported-delete-operation
#   pylint could not understand that JSON fields are dicts
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

from django.contrib.auth.models import User, Group, Permission
from django.db import transaction
from django.db import models

from adwp_base.errors import raise_AdwpEx as err


class Role(models.Model):
    name = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)
    childs = models.ManyToManyField("self", symmetrical=False, blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    user = models.ManyToManyField(User, blank=True)
    group = models.ManyToManyField(Group, blank=True)

    def get_permissions(self, role=None):
        role_list = []
        perm_list = []
        if role is None:
            role = self

        def get_perm(role, perm_list, role_list):
            if role in role_list:
                return
            role_list.append(role)
            for p in role.permissions.all():
                if p not in perm_list:
                    perm_list.append(p)
            for child in role.childs.all():
                get_perm(child, perm_list, role_list)

        get_perm(role, perm_list, role_list)
        return perm_list

    def get_permissions_without_role(self, role_list):
        perm_list = {}
        for r in role_list:
            if r == self:
                continue
            for perm in self.get_permissions(r):
                perm_list[perm.codename] = True
        return perm_list

    def add_user(self, user):
        if self in user.role_set.all():
            err('ROLE_ERROR', f'User "{user.username}" already has role "{self.name}"')
        with transaction.atomic():
            self.user.add(user)
            self.save()
            for perm in self.get_permissions():
                user.user_permissions.add(perm)
        return self

    def remove_user(self, user):
        user_roles = user.role_set.all()
        if self not in user_roles:
            err('ROLE_ERROR', f'User "{user.username}" does not has role "{self.name}"')
        perm_list = self.get_permissions_without_role(user_roles)
        with transaction.atomic():
            self.user.remove(user)
            self.save()
            for perm in self.get_permissions():
                if perm.codename not in perm_list:
                    user.user_permissions.remove(perm)


class RoleMigration(models.Model):
    version = models.PositiveIntegerField(primary_key=True)
    date = models.DateTimeField(auto_now=True)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    profile = models.JSONField(default=str)
