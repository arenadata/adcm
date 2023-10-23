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
from api_v2.adcm.serializers import AdcmSerializer
from api_v2.config.utils import get_config_schema
from api_v2.config.views import ConfigLogViewSet
from api_v2.views import CamelCaseGenericViewSet
from cm.models import ADCM, ConfigLog, PrototypeConfig
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK


class ADCMViewSet(RetrieveModelMixin, CamelCaseGenericViewSet):
    queryset = ADCM.objects.prefetch_related("concerns").all()
    serializer_class = AdcmSerializer

    def get_object(self, *args, **kwargs):  # pylint: disable=unused-argument
        return super().get_queryset().first()


class ADCMConfigView(ConfigLogViewSet):  # pylint: disable=too-many-ancestors
    def get_queryset(self, *args, **kwargs):
        return (
            ConfigLog.objects.select_related("obj_ref__adcm__prototype")
            .filter(obj_ref__adcm__isnull=False)
            .order_by("-pk")
        )

    def get_parent_object(self) -> ADCM | None:
        return ADCM.objects.first()

    @action(methods=["get"], detail=True, url_path="config-schema", url_name="config-schema")
    def config_schema(self, request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        instance = self.get_parent_object()
        schema = get_config_schema(
            object_=instance,
            prototype_configs=PrototypeConfig.objects.filter(prototype=instance.prototype, action=None).order_by("pk"),
        )

        return Response(data=schema, status=HTTP_200_OK)
