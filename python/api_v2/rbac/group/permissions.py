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

from adcm.permissions import VIEW_GROUP_PERMISSION
from rest_framework.exceptions import NotFound
from rest_framework.permissions import DjangoModelPermissions


class GroupPermissions(DjangoModelPermissions):
    method_permissions_map = {
        "patch": [(VIEW_GROUP_PERMISSION, NotFound)],
        "delete": [(VIEW_GROUP_PERMISSION, NotFound)],
    }

    def has_permission(self, request, view):
        for permission, error in self.method_permissions_map.get(request.method.lower(), []):
            if not request.user.has_perm(perm=permission):
                raise error

        return super().has_permission(request, view)