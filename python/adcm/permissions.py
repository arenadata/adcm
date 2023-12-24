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

from typing import Any, Sequence

from audit.utils import audit
from cm.errors import AdcmEx
from cm.models import ADCMEntity
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from guardian.shortcuts import get_objects_for_user
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import (
    DjangoModelPermissions,
    DjangoObjectPermissions,
    IsAuthenticated,
)

VIEW_CLUSTER_PERM = "cm.view_cluster"
VIEW_CLUSTER_UPGRADE_PERM = "cm.view_upgrade_of_cluster"
VIEW_SERVICE_PERM = "cm.view_clusterobject"
VIEW_ACTION_PERM = "cm.view_action"
CHANGE_MM_PERM = "change_maintenance_mode"
ADD_SERVICE_PERM = "add_service_to"
RUN_ACTION_PERM_PREFIX = "cm.run_action_"
ADD_HOST_TO = "add_host_to"
VIEW_HOST_PERM = "cm.view_host"
VIEW_PROVIDER_PERM = "cm.view_hostprovider"
VIEW_PROVIDER_UPGRADE_PERM = "cm.view_upgrade_of_hostprovider"
VIEW_COMPONENT_PERM = "cm.view_servicecomponent"
VIEW_HC_PERM = "cm.view_hostcomponent"
VIEW_CONFIG_PERM = "cm.view_configlog"
VIEW_GROUP_CONFIG_PERM = "cm.view_groupconfig"
VIEW_IMPORT_PERM = "view_import_of"
CHANGE_IMPORT_PERM = "change_import_of"
VIEW_CLUSTER_BIND = "view_clusterbind"
VIEW_TASKLOG_PERMISSION = "cm.view_tasklog"
VIEW_JOBLOG_PERMISSION = "cm.view_joblog"
VIEW_LOGSTORAGE_PERMISSION = "cm.view_logstorage"
VIEW_USER_PERMISSION = "rbac.view_user"
VIEW_GROUP_PERMISSION = "rbac.view_group"
VIEW_ROLE_PERMISSION = "rbac.view_role"
VIEW_POLICY_PERMISSION = "rbac.view_policy"


class DjangoObjectPermissionsAudit(DjangoObjectPermissions):
    @audit
    def has_permission(self, request, view):
        return super().has_permission(request, view)


class DjangoModelPermissionsAudit(DjangoModelPermissions):
    @audit
    def has_permission(self, request, view):
        return super().has_permission(request, view)


class CustomModelPermissionsByMethod(DjangoModelPermissionsAudit):
    method_permissions_map = {
        # Example:
        # "get": [("app_label.permission", ErrorToRaise), ...]
    }

    @audit
    def has_permission(self, request, view):
        for permission, error in view.method_permissions_map.get(request.method.lower(), []):
            if not request.user.has_perm(perm=permission):
                raise error

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


def get_object_for_user(user: User, perms: str | Sequence[str], klass: type[Model], **kwargs) -> Any:
    try:
        queryset = get_objects_for_user(user, perms, klass)

        return queryset.get(**kwargs)
    except ObjectDoesNotExist:
        model = klass
        if not hasattr(klass, "_default_manager"):
            model = klass.model

        error_code = "NO_MODEL_ERROR_CODE"
        if hasattr(model, "__error_code__"):
            error_code = model.__error_code__

        raise AdcmEx(error_code) from None


def check_custom_perm(user: User, action_type: str, model: str, obj: Any, second_perm=None) -> None:
    if user.has_perm(f"cm.{action_type}_{model}", obj):
        return

    if second_perm is not None and user.has_perm(f"cm.{second_perm}"):
        return

    raise PermissionDenied()


def check_config_perm(user: User, action_type: str, model: str, obj: ADCMEntity) -> None:
    if user.has_perm(f"cm.{action_type}_config_of_{model}", obj):
        return

    if model == "adcm" and user.has_perm(f"cm.{action_type}_settings_of_{model}"):
        return

    raise PermissionDenied()


class ChangeMMPermissions(DjangoObjectPermissions):
    perms_map = {
        "POST": [],
    }

    @audit
    def has_permission(self, request, view) -> bool:
        return super().has_permission(request=request, view=view)
