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

from adcm.mixins import ParentObject
from adcm.permissions import check_config_perm
from cm.models import ADCM, ConfigLog, PrototypeConfig
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from api_v2.adcm.serializers import AdcmSerializer
from api_v2.api_schema import ErrorSerializer
from api_v2.config.serializers import ConfigLogListSerializer, ConfigLogSerializer
from api_v2.config.utils import get_config_schema
from api_v2.config.views import ConfigLogViewSet
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    retrieve=extend_schema(
        operation_id="getADCMObject",
        summary="GET ADCM object",
        description="GET ADCM object.",
        responses={200: AdcmSerializer},
    ),
)
class ADCMViewSet(RetrieveModelMixin, ADCMGenericViewSet):
    queryset = ADCM.objects.prefetch_related("concerns").all()
    serializer_class = AdcmSerializer

    def get_object(self, *args, **kwargs):  # noqa: ARG001, ARG002
        return super().get_queryset().first()


@extend_schema_view(
    retrieve=extend_schema(
        operation_id="getADCMConfig",
        summary="GET ADCM config",
        description="Get ADCM configuration information.",
        responses={200: ConfigLogSerializer, 404: ErrorSerializer},
    ),
    list=extend_schema(
        operation_id="getADCMConfigs",
        summary="GET ADCM config vesions",
        description="Get information about ADCM config versions.",
        parameters=[
            OpenApiParameter(
                name="isCurrent",
                required=False,
                location=OpenApiParameter.QUERY,
                description="Sign of the current configuration.",
                type=bool,
            )
        ],
        responses={200: ConfigLogListSerializer, 404: ErrorSerializer},
    ),
    create=extend_schema(
        operation_id="postADCMConfigs",
        summary="POST ADCM configs",
        description="Create a new version of the ADCM configuration.",
        responses={201: ConfigLogSerializer, 400: ErrorSerializer, 403: ErrorSerializer, 404: ErrorSerializer},
    ),
)
class ADCMConfigView(ConfigLogViewSet):
    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        return (
            ConfigLog.objects.select_related("obj_ref__adcm__prototype")
            .filter(obj_ref__adcm__isnull=False)
            .order_by("-pk")
        )

    def get_parent_object(self) -> ADCM | None:
        return ADCM.objects.first()

    @extend_schema(
        summary="Get ADCM config schema",
        description="Full representation of ADCM config.",
        responses={200: AdcmSerializer},
    )
    @action(methods=["get"], detail=True, url_path="config-schema", url_name="config-schema")
    def config_schema(self, request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        instance = self.get_parent_object()
        schema = get_config_schema(
            object_=instance,
            prototype_configs=PrototypeConfig.objects.filter(prototype=instance.prototype, action=None).order_by("pk"),
        )

        return Response(data=schema, status=HTTP_200_OK)

    def _check_create_permissions(self, request: Request, parent_object: ADCM | None) -> None:
        if parent_object is None:
            raise NotFound("Can't find config's parent object")

        check_config_perm(user=request.user, action_type="change", model=ADCM._meta.model_name, obj=parent_object)

    def _check_parent_permissions(self, parent_object: ParentObject = None):
        pass
