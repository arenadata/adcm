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

from copy import deepcopy
from typing import NoReturn, cast
import json

from adcm.feature_flags import use_new_config_processing
from adcm.mixins import GetParentObjectMixin, ParentObject
from adcm.permissions import VIEW_CONFIG_PERM, check_config_perm
from application.migration.config import update_configuration_of_host_group, update_configuration_of_object
from cm.api import update_obj_config
from cm.errors import AdcmEx
from cm.models import ADCM, ConfigHostGroup, ConfigLog, MainObject, PrototypeConfig
from cm.services.config import (
    convert_attr_to_adcm_meta,
    represent_json_type_as_string,
)
from cm.services.config._base import convert_adcm_meta_to_attr, represent_string_as_json_type
from django.contrib.contenttypes.models import ContentType
from guardian.mixins import PermissionListMixin
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer, ValidationError
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
)
import core

from api_v2.generic.config.filters import ConfigLogFilter
from api_v2.generic.config.serializers import ConfigLogListSerializer, ConfigLogSerializer
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
        if isinstance(parent_object, ConfigHostGroup):
            owner = cast(MainObject, parent_object.object)
            group = parent_object
            convert_serialized_config = self.convert_group_config
            return update_configuration_of_host_group(
                input_config=serializer.validated_data,
                convert=convert_serialized_config,
                description=serializer.validated_data.get("description", ""),
                owner=owner,
                group=group,
            )

        owner: MainObject | ADCM | ConfigHostGroup = parent_object
        convert_serialized_config = self.convert_main_config

        return update_configuration_of_object(
            input_config=serializer.validated_data,
            convert=convert_serialized_config,
            description=serializer.validated_data.get("description", ""),
            owner=owner,
        )

    def convert_main_config(
        self, configuration: dict, specification: core.config.spec.FullSpec
    ) -> core.config.Configuration:
        attributes = self.convert_to_attributes(attr=configuration["attr"], allowed_keys={"isActive"})
        values = self.convert_values(input_values=configuration["config"], specification=specification)
        return core.config.Configuration(values=values, attributes=attributes)

    def convert_group_config(
        self, configuration: dict, specification: core.config.spec.FullSpec
    ) -> core.config.Configuration:
        attributes = self.convert_to_attributes(attr=configuration["attr"], allowed_keys={"isActive", "isSynchronized"})
        values = self.convert_values(input_values=configuration["config"], specification=specification)
        return core.config.Configuration(values=values, attributes=attributes)

    def convert_values(self, input_values: dict, specification: core.config.spec.FullSpec):
        values = deepcopy(input_values)

        for name, param in specification.parameters.items():
            if param.type == core.config.spec.p.ParameterType.JSON:
                json_value = core.config.get_by_full_name(name=name, values=values)
                if json_value is not None:
                    try:
                        parsed_value = json.loads(json_value)
                    except (json.JSONDecodeError, TypeError) as e:
                        raise AdcmEx(
                            code="CONFIG_KEY_ERROR",
                            msg=f"Value of '{name}' must be correct json string.",
                        ) from e

                    core.config.set_by_full_name(new_value=parsed_value, name=name, values=values)

        return values

    def convert_to_attributes(
        self, attr: dict, allowed_keys: set[str]
    ) -> dict[core.config.ParameterFullName, core.config.Attributes]:
        attributes = {}

        for name, value in attr.items():
            if not isinstance(value, dict):
                raise ValidationError("adcmMeta values should be dictionaries")

            if not (value.keys() and allowed_keys.issuperset(value.keys())):
                raise AdcmEx(
                    code="ATTRIBUTE_ERROR",
                    msg=f"Incorrect attributes, at least one of {', '.join(sorted(allowed_keys))}, extra not allowed",
                )

            try:
                attributes[name] = core.config.Attributes(
                    is_active=value.get("isActive"), is_synced=value.get("isSynchronized")
                )
            except ValueError as e:
                raise AdcmEx(code="ATTRIBUTE_ERROR", msg=str(e)) from e

        return attributes

    def create(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        parent_object = self.get_parent_object(raise_=NotFound())

        self._check_parent_permissions(parent_object=parent_object)
        self._check_create_permissions(request=request, parent_object=parent_object)

        serializer = self.get_serializer(data=request.data, context={"object_": parent_object})
        serializer.is_valid(raise_exception=True)

        func = self.new_create if use_new_config_processing(headers=request.headers) else self.old_create

        config_log = func(parent_object=parent_object, serializer=serializer)

        config_log.attr = convert_attr_to_adcm_meta(attr=config_log.attr)
        config_log.config = represent_json_type_as_string(prototype=parent_object.prototype, value=config_log.config)

        return Response(data=self.get_serializer(config_log).data, status=HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        parent_object = self.get_parent_object()
        self._check_parent_permissions(parent_object)
        instance = self.get_object()
        instance.attr = convert_attr_to_adcm_meta(attr=instance.attr)
        instance.config = represent_json_type_as_string(prototype=parent_object.prototype, value=instance.config)
        serializer = self.get_serializer(instance)

        return Response(data=serializer.data, status=HTTP_200_OK)

    def list(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        self._check_parent_permissions()
        return super().list(request, *args, **kwargs)

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
