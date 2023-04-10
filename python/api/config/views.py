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

from api.base_view import GenericUIView
from api.config.serializers import (
    ConfigHistorySerializer,
    ConfigObjectConfigSerializer,
    HistoryCurrentPreviousConfigSerializer,
    ObjectConfigRestoreSerializer,
    ObjectConfigUpdateSerializer,
)
from api.utils import check_obj, create, update
from audit.utils import audit
from cm.adcm_config import ansible_encrypt_and_format, ui_config
from cm.errors import AdcmEx
from cm.models import ConfigLog, ObjectConfig, get_model_by_type
from django.conf import settings
from guardian.mixins import PermissionListMixin
from rbac.viewsets import DjangoOnlyObjectPermissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def get_config_version(queryset, objconf, version) -> ConfigLog:
    if version == "previous":
        ver = objconf.previous
    elif version == "current":
        ver = objconf.current
    else:
        ver = version
    try:
        config_log = queryset.get(obj_ref=objconf, id=ver)
    except ConfigLog.DoesNotExist:
        raise AdcmEx("CONFIG_NOT_FOUND") from None

    return config_log


def type_to_model(object_type):
    if object_type == "provider":
        object_type = "hostprovider"

    if object_type == "service":
        object_type = "clusterobject"

    if object_type == "component":
        object_type = "servicecomponent"

    return object_type


def get_obj(object_type, object_id):
    model = get_model_by_type(object_type)
    obj = model.obj.get(id=object_id)
    object_config = check_obj(ObjectConfig, {type_to_model(object_type): obj}, "CONFIG_NOT_FOUND")

    return obj, object_config


def get_object_type_id_version(**kwargs):
    object_type = kwargs.get("object_type")
    object_id = kwargs.get(f"{object_type}_id") or kwargs.get(f"{object_type}_pk")
    version = kwargs.get("version")

    return object_type, object_id, version


def has_config_perm(user, action_type, object_type, obj):
    """
    Checks permission to view/change config of any object
    """
    model = type_to_model(object_type)
    if user.has_perm(f"cm.{action_type}_config_of_{model}", obj):
        return True
    if model == "adcm" and user.has_perm(f"cm.{action_type}_settings_of_{model}"):
        return True
    return False


def check_config_perm(user, action_type, object_type, obj):
    if not has_config_perm(user, action_type, object_type, obj):
        raise PermissionDenied()


class ConfigView(GenericUIView):
    queryset = ConfigLog.objects.all()
    serializer_class = HistoryCurrentPreviousConfigSerializer
    permission_classes = (IsAuthenticated,)
    ordering = ["id"]

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        object_type, object_id, _ = get_object_type_id_version(**kwargs)
        model = get_model_by_type(object_type)
        obj = model.obj.get(id=object_id)
        serializer = self.get_serializer(obj)

        return Response(serializer.data)


class ConfigHistoryView(PermissionListMixin, GenericUIView):
    queryset = ConfigLog.objects.all()
    serializer_class = ConfigHistorySerializer
    serializer_class_post = ObjectConfigUpdateSerializer
    permission_required = ["cm.view_configlog"]
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):
        if self.request.user.has_perm("cm.view_settings_of_adcm"):
            return super().get_queryset(*args, **kwargs) | ConfigLog.objects.filter(obj_ref__adcm__isnull=False)
        else:
            return super().get_queryset(*args, **kwargs).filter(obj_ref__adcm__isnull=True)

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        object_type, object_id, _ = get_object_type_id_version(**kwargs)
        obj, object_config = get_obj(object_type, object_id)
        config_log = self.get_queryset().filter(obj_ref=object_config).order_by("-id")
        serializer = self.get_serializer(config_log, many=True, context={"request": request, "object": obj})

        return Response(serializer.data)

    @audit
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        object_type, object_id, _ = get_object_type_id_version(**kwargs)
        obj, object_config = get_obj(object_type, object_id)
        check_config_perm(request.user, "change", object_type, obj)
        try:
            config_log = self.get_queryset().get(obj_ref=object_config, id=object_config.current)
        except ConfigLog.DoesNotExist:
            raise AdcmEx("CONFIG_NOT_FOUND") from None

        serializer = self.get_serializer(config_log, data=request.data)

        return create(serializer, ui=self._is_for_ui(), obj=obj)


class ConfigVersionView(PermissionListMixin, GenericUIView):
    queryset = ConfigLog.objects.all()
    permission_classes = (DjangoOnlyObjectPermissions,)
    serializer_class = ConfigObjectConfigSerializer
    permission_required = ["cm.view_configlog"]
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):
        if self.request.user.has_perm("cm.view_settings_of_adcm"):
            return super().get_queryset(*args, **kwargs) | ConfigLog.objects.filter(obj_ref__adcm__isnull=False)
        else:
            return super().get_queryset(*args, **kwargs).filter(obj_ref__adcm__isnull=True)

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        object_type, object_id, version = get_object_type_id_version(**kwargs)
        obj, object_config = get_obj(object_type, object_id)
        config_log = get_config_version(self.get_queryset(), object_config, version)
        ui_config_data = ui_config(obj, config_log)
        for item in ui_config_data:
            if item["type"] != "secretfile":
                continue

            if not item["value"]:
                continue

            if settings.ANSIBLE_VAULT_HEADER not in item["value"]:
                encrypted_value = ansible_encrypt_and_format(msg=item["value"])
                item["value"] = encrypted_value
            else:
                encrypted_value = item["value"]

            if not item["subname"]:
                config_log.config[item["name"]] = encrypted_value
            else:
                config_log.config[item["name"]][item["subname"]] = encrypted_value

        if self._is_for_ui():
            config_log.config = ui_config_data

        serializer = self.get_serializer(config_log)

        return Response(serializer.data)


class ConfigHistoryRestoreView(PermissionListMixin, GenericUIView):
    queryset = ConfigLog.objects.all()
    serializer_class = ObjectConfigRestoreSerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = ["cm.view_configlog"]
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):
        if self.request.user.has_perm("cm.view_settings_of_adcm"):
            return super().get_queryset(*args, **kwargs) | ConfigLog.objects.filter(obj_ref__adcm__isnull=False)
        else:
            return super().get_queryset(*args, **kwargs).filter(obj_ref__adcm__isnull=True)

    @audit
    def patch(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        object_type, object_id, version = get_object_type_id_version(**kwargs)
        obj, object_config = get_obj(object_type, object_id)
        check_config_perm(request.user, "change", object_type, obj)
        config_log = get_config_version(self.get_queryset(), object_config, version)
        serializer = self.get_serializer(config_log, data=request.data)

        return update(serializer)
