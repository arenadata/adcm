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

from typing import NoReturn, cast

from adcm.feature_flags import use_new_config_processing
from adcm.mixins import GetParentObjectMixin, ParentObject
from adcm.permissions import VIEW_CONFIG_PERM, check_config_perm
from application.migration.config import update_configuration_of_host_group, update_configuration_of_object
from cm.api import update_obj_config
from cm.converters import orm_object_to_core_descriptor
from cm.errors import AdcmEx
from cm.models import ADCM, ConfigHostGroup, ConfigLog, MainObject, PrototypeConfig
from cm.services.config import (
    convert_attr_to_adcm_meta,
    represent_json_type_as_string,
)
from cm.services.config._base import convert_adcm_meta_to_attr, represent_string_as_json_type
from django.contrib.contenttypes.models import ContentType
from guardian.mixins import PermissionListMixin
from infra.services import get_config_service
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
)
import core

from api_v2.generic.config.filters import ConfigLogFilter
from api_v2.generic.config.serializers import ConfigLogListSerializer, ConfigLogSerializer
from api_v2.utils.config import convert_group_config, convert_json_fields_to_strings, convert_main_config
from api_v2.views import ADCMGenericViewSet


class ConfigLogViewSet(
    PermissionListMixin,
    ListModelMixin,
    RetrieveModelMixin,
    GetParentObjectMixin,
    ADCMGenericViewSet,
):
    queryset = ConfigLog.objects.select_related(
        "obj_ref__cluster__prototype",
        "obj_ref__service__prototype",
        "obj_ref__component__prototype",
        "obj_ref__provider__prototype",
        "obj_ref__host__prototype",
    ).order_by("-pk")
    permission_required = [VIEW_CONFIG_PERM]
    filterset_class = ConfigLogFilter

    def get_queryset(self, *args, **kwargs):
        parent_object = self.get_parent_object()

        if parent_object is None:
            raise NotFound

        if not parent_object.config:
            return ConfigLog.objects.none()

        return super().get_queryset(*args, **kwargs).filter(obj_ref=parent_object.config)

    def get_serializer_class(self):
        if self.action == "list":
            return ConfigLogListSerializer

        return ConfigLogSerializer

    def handle_exception(self, exc: Exception) -> Response:
        if isinstance(exc, core.config.OperationError):
            exc = AdcmEx(code="CONFIG_OPERATION_ERROR", msg=exc.args[0])

        return super().handle_exception(exc)

    def old_create(self, parent_object, serializer):
        prototype_configs = tuple(
            PrototypeConfig.objects.filter(prototype=parent_object.prototype, type="json", action=None)
        )

        return update_obj_config(
            obj_conf=parent_object.config,
            config=represent_string_as_json_type(
                prototype_configs=prototype_configs, value=serializer.validated_data["config"]
            ),
            attr=convert_adcm_meta_to_attr(adcm_meta=serializer.validated_data["attr"]),
            description=serializer.validated_data.get("description", ""),
        )

    def new_create(self, parent_object: MainObject | ADCM | ConfigHostGroup, serializer: BaseSerializer):
        service = get_config_service()

        if isinstance(parent_object, ConfigHostGroup):
            owner = cast(MainObject, parent_object.object)
            group = parent_object
            convert_serialized_config = convert_group_config
            config_id = update_configuration_of_host_group(
                input_config=serializer.validated_data,
                convert=convert_serialized_config,
                description=serializer.validated_data.get("description", ""),
                owner=owner,
                group=group,
                config_service=service,
            )
        else:
            owner: MainObject | ADCM | ConfigHostGroup = parent_object
            convert_serialized_config = convert_main_config

            config_id = update_configuration_of_object(
                input_config=serializer.validated_data,
                convert=convert_serialized_config,
                description=serializer.validated_data.get("description", ""),
                owner=owner,
                config_service=service,
            )

        return ConfigLog.objects.get(id=config_id)

    def create(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        parent_object = self.get_parent_object(raise_=NotFound())

        self._check_parent_permissions(parent_object=parent_object)
        self._check_create_permissions(request=request, parent_object=parent_object)

        serializer = self.get_serializer(data=request.data, context={"object_": parent_object})
        serializer.is_valid(raise_exception=True)

        if use_new_config_processing(headers=request.headers):
            create_new = self.new_create
            convert = self.new_convert
        else:
            create_new = self.old_create
            convert = self.old_convert

        config_log = create_new(parent_object=parent_object, serializer=serializer)
        config_log = convert(config_log, parent_object)

        return Response(data=self.get_serializer(config_log).data, status=HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        parent_object = self.get_parent_object(raise_=NotFound())
        self._check_parent_permissions(parent_object)

        instance = self.get_object()
        func = self.new_convert if use_new_config_processing(headers=request.headers) else self.old_convert

        instance = func(instance, parent_object)
        serializer = self.get_serializer(instance)

        return Response(data=serializer.data, status=HTTP_200_OK)

    def list(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        self._check_parent_permissions()
        return super().list(request, *args, **kwargs)

    def old_convert(self, config_log: ConfigLog, parent_object: ParentObject) -> ConfigLog:
        config_log.attr = convert_attr_to_adcm_meta(attr=config_log.attr)
        config_log.config = represent_json_type_as_string(prototype=parent_object.prototype, value=config_log.config)
        return config_log

    def new_convert(self, config_log: ConfigLog, parent_object: ParentObject) -> ConfigLog:
        match parent_object:
            case ConfigHostGroup():
                object_ = parent_object.object
                if not object_:
                    raise RuntimeError(f"Host group does not have owner: {parent_object}")

                owner = orm_object_to_core_descriptor(object_)
            case _:
                owner = orm_object_to_core_descriptor(parent_object)

        config_log.attr = convert_attr_to_adcm_meta(attr=config_log.attr)

        config_service = get_config_service()
        specification = config_service.retrieve_partial_specification(
            owner=owner, only_for_types=(core.config.spec.p.JSONParameter,)
        )
        config_log.config = convert_json_fields_to_strings(values=config_log.config, spec=specification)

        return config_log

    def _check_create_permissions(self, request: Request, parent_object: ParentObject) -> None:
        owner_object = parent_object.object if isinstance(parent_object, ConfigHostGroup) else parent_object

        owner_view_perm = f"cm.view_{owner_object.__class__.__name__.lower()}"
        if owner_object is None or not (
            request.user.has_perm(perm=owner_view_perm, obj=owner_object) or request.user.has_perm(perm=owner_view_perm)
        ):
            raise NotFound("Can't find config's parent object")

        if owner_object.config is None:
            self.on_config_absent_for_owner(owner_object)

        check_config_perm(
            user=request.user,
            action_type="change",
            model=ContentType.objects.get_for_model(model=owner_object).model,
            obj=owner_object,
        )

    def _check_parent_permissions(self, parent_object: ParentObject | None = None):
        parent_obj = parent_object or self.get_parent_object()
        parent_view_perm = f"cm.view_{parent_obj.__class__.__name__.lower()}"
        parent_config_view_perm = "cm.view_objectconfig"

        if parent_obj is None:
            raise NotFound

        if not (
            self.request.user.has_perm(parent_view_perm, parent_obj) or self.request.user.has_perm(parent_view_perm)
        ):
            raise NotFound

        if not (
            self.request.user.has_perm(parent_config_view_perm, parent_obj.config)
            or self.request.user.has_perm(parent_config_view_perm)
        ):
            raise PermissionDenied

    def on_config_absent_for_owner(self, owner_object: MainObject) -> NoReturn:
        _ = owner_object
        raise AdcmEx(code="CONFIG_NOT_FOUND", msg="This object has no config")
