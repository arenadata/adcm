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
from cm.services.bundle import ADCMBundlePathResolver
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from api_v2.adcm.serializers import AdcmSerializer
from api_v2.api_schema import DefaultParams, ErrorSerializer, responses
from api_v2.generic.action.api_schema import document_action_viewset
from api_v2.generic.action.audit import audit_action_viewset
from api_v2.generic.action.views import ActionViewSet
from api_v2.generic.config.api_schema import document_config_viewset
from api_v2.generic.config.audit import audit_config_viewset
from api_v2.generic.config.utils import get_config_schema
from api_v2.generic.config.views import ConfigLogViewSet
from api_v2.utils.audit import adcm_audit_object
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    retrieve=extend_schema(
        operation_id="getADCMObject",
        summary="GET ADCM object",
        description="GET ADCM object.",
        responses=responses(success=(HTTP_200_OK, AdcmSerializer)),
    ),
)
class ADCMViewSet(RetrieveModelMixin, ADCMGenericViewSet):
    queryset = ADCM.objects.prefetch_related("concerns").all()
    serializer_class = AdcmSerializer

    def get_object(self, *args, **kwargs):  # noqa: ARG001, ARG002
        return super().get_queryset().first()


@document_config_viewset(object_type="ADCM", operation_id_variant="ADCM")
@audit_config_viewset(type_in_name="ADCM", retrieve_owner=adcm_audit_object)
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
        examples=DefaultParams.CONFIG_SCHEMA_EXAMPLE,
        responses={HTTP_200_OK: dict, HTTP_403_FORBIDDEN: ErrorSerializer},
    )
    @action(methods=["get"], detail=True, url_path="config-schema", url_name="config-schema")
    def config_schema(self, request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        instance = self.get_parent_object()
        path_resolver = ADCMBundlePathResolver()
        schema = get_config_schema(
            object_=instance,
            prototype_configs=PrototypeConfig.objects.filter(prototype=instance.prototype, action=None).order_by("pk"),
            path_resolver=path_resolver,
        )

        return Response(data=schema, status=HTTP_200_OK)

    def _check_create_permissions(self, request: Request, parent_object: ADCM | None) -> None:
        if parent_object is None:
            raise NotFound("Can't find config's parent object")

        check_config_perm(user=request.user, action_type="change", model=ADCM._meta.model_name, obj=parent_object)

    def _check_parent_permissions(self, parent_object: ParentObject = None):
        pass


@document_action_viewset(object_type="ADCM", operation_id_variant="ADCM")
@audit_action_viewset(retrieve_owner=adcm_audit_object)
class ADCMActionViewSet(ActionViewSet):
    def get_parent_object(self):
        return ADCM.objects.first()

    def list(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        self.parent_object = self.get_parent_object()

        return self._list_actions_available_to_user(request)
