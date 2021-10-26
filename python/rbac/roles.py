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

"""RBAC Role classes"""

from guardian.models import UserObjectPermission


class ModelRole:
    def __init__(self, **kwargs):
        pass

    def apply(self, role, user, obj=None):
        for perm in role.get_permissions():
            user.user_permissions.add(perm)


class ObjectRole:
    def __init__(self, **kwargs):
        pass

    def apply(self, role, user, obj):
        for perm in role.get_permissions():
            UserObjectPermission.objects.assign_perm(perm, user, obj=obj)
