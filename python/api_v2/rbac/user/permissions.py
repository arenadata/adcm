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

from adcm.permissions import VIEW_USER_PERMISSION
from rest_framework.exceptions import NotFound
from rest_framework.permissions import DjangoModelPermissions


class UserPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_permission(self, request, view):
        if view.action not in ("create", "list") and not request.user.has_perm(VIEW_USER_PERMISSION):
            raise NotFound()

        if not request.user.has_perms(self.get_required_permissions(request.method, view.queryset.model)):
            return False

        return super().has_permission(request, view)
