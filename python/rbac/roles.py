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
from rbac.models import PolicyPermission


class ModelRole:
    def __init__(self, **kwargs):
        pass

    def apply(self, policy, role, user, group=None, obj=None):
        for perm in role.get_permissions():
            if group is not None:
                group.permissions.add(perm)
                pp = PolicyPermission(policy=policy, group=group, permission=perm)
                pp.save()
                policy.model_perm.add(pp)
            if user is not None:
                user.user_permissions.add(perm)
                pp = PolicyPermission(policy=policy, user=user, permission=perm)
                pp.save()
                policy.model_perm.add(pp)


class ObjectRole:
    def __init__(self, **kwargs):
        pass

    def apply(self, policy, role, user, group=None, obj_list=None):
        for obj in obj_list:
            for perm in role.get_permissions():
                if user is not None:
                    uop = UserObjectPermission.objects.assign_perm(perm, user, obj)
                    policy.object_perm.add(uop)
                if group is not None:
                    uop = UserObjectPermission.objects.assign_perm(perm, group, obj)
                    policy.object_perm.add(uop)
