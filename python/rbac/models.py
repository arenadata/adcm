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
from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)
    childs = models.ManyToManyField("self", symmetrical=False, blank=True)
    permissions = models.ManyToManyField(
        Permission, blank=True, related_name='rbac_role_permissions'
    )
    user = models.ManyToManyField(User, blank=True, related_name='rbac_role_user')
    group = models.ManyToManyField(Group, blank=True, related_name='rbac_role_group')


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    profile = models.JSONField(default=str)
