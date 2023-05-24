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

from audit.utils import audit
from cm.errors import AdcmEx
from rest_framework.permissions import (
    DjangoModelPermissions,
    DjangoObjectPermissions,
    IsAuthenticated,
)

VIEW_ACTION_PERM = "cm.view_action"
VIEW_CLUSTER_PERM = "cm.view_cluster"
VIEW_HOST_PERM = "cm.view_host"
VIEW_PROVIDER_PERM = "cm.view_hostprovider"


class DjangoObjectPermissionsAudit(DjangoObjectPermissions):
    @audit
    def has_permission(self, request, view):
        return super().has_permission(request, view)


class DjangoModelPermissionsAudit(DjangoModelPermissions):
    @audit
    def has_permission(self, request, view):
        return super().has_permission(request, view)


class IsAuthenticatedAudit(IsAuthenticated):
    @audit
    def has_permission(self, request, view):
        return super().has_permission(request, view)


class SuperuserOnlyMixin:
    not_superuser_error_code = None

    def get_queryset(self, *args, **kwargs):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.model.objects.none()

        if not self.request.user.is_superuser:
            if self.not_superuser_error_code:
                raise AdcmEx(self.not_superuser_error_code)

            return self.queryset.model.objects.none()

        return super().get_queryset(*args, **kwargs)
