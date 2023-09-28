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

from api_v2.config.serializers import ConfigLogListSerializer, ConfigLogSerializer
from api_v2.config.utils import (
    convert_adcm_meta_to_attr,
    convert_attr_to_adcm_meta,
    get_config_schema,
)
from api_v2.views import CamelCaseGenericViewSet
from cm.api import update_obj_config
from cm.errors import AdcmEx
from cm.models import ConfigLog
from django.contrib.contenttypes.models import ContentType
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.mixins import GetParentObjectMixin
from adcm.permissions import VIEW_CONFIG_PERM, check_config_perm


class ConfigLogViewSet(
    PermissionListMixin,
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    GetParentObjectMixin,
    CamelCaseGenericViewSet,
):  # pylint: disable=too-many-ancestors
    queryset = ConfigLog.objects.select_related(
        "obj_ref__cluster__prototype",
        "obj_ref__clusterobject__prototype",
        "obj_ref__servicecomponent__prototype",
        "obj_ref__hostprovider__prototype",
        "obj_ref__host__prototype",
    ).order_by("-pk")
    permission_required = [VIEW_CONFIG_PERM]
    filter_backends = []

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

    def create(self, request, *args, **kwargs) -> Response:
        parent_object = self.get_parent_object()

        if parent_object is None:
            raise NotFound("Can't find config's parent object")

        if parent_object.config is None:
            raise AdcmEx(code="CONFIG_NOT_FOUND", msg="This object has no config")

        check_config_perm(
            user=request.user,
            action_type="change",
            model=ContentType.objects.get_for_model(model=parent_object).model,
            obj=parent_object,
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        config_log = update_obj_config(
            obj_conf=parent_object.config,
            config=serializer.validated_data["config"],
            attr=convert_adcm_meta_to_attr(adcm_meta=serializer.validated_data["attr"]),
            description=serializer.validated_data.get("description", ""),
        )

        config_log.attr = convert_attr_to_adcm_meta(attr=config_log.attr)

        return Response(data=self.get_serializer(config_log).data, status=HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs) -> Response:
        instance = self.get_object()
        instance.attr = convert_attr_to_adcm_meta(attr=instance.attr)
        serializer = self.get_serializer(instance)

        return Response(data=serializer.data, status=HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="schema", url_name="schema")
    def config_schema(self, request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        schema = get_config_schema(parent_object=self.get_parent_object())

        return Response(data=schema, status=HTTP_200_OK)
