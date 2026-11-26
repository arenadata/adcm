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

from adcm.permissions import VIEW_TASKLOG_PERMISSION
from django.contrib.contenttypes.models import ContentType
from guardian.mixins import PermissionListMixin
from rest_framework.permissions import DjangoObjectPermissions, IsAuthenticated


class TaskPermissions(DjangoObjectPermissions):
    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.change_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_permission(self, request, view):  # noqa: ARG002
        return True


class TaskVisibilityMixin(PermissionListMixin):
    """
    Restricts a `TaskLog`-based view's queryset to tasks the user may see:
    view permission is required and ADCM-owned tasks are hidden from non-superusers.
    """

    permission_classes = [IsAuthenticated, TaskPermissions]
    permission_required = [VIEW_TASKLOG_PERMISSION]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(object_type=ContentType.objects.get(app_label="cm", model="adcm"))

        return queryset
