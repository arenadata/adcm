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

from api_v2.api_schema import responses
from api_v2.utils.di import inject
from core import secrets
from core.adcm import ADCMRepoI
from dishka import FromDishka
from drf_spectacular.utils import extend_schema
from integrations.consul import ConsulBackend
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from rest_framework.views import APIView

from health.checks import run_readiness_checks
from health.serializers import LivenessSerializer, ReadinessSerializer


class ReadinessView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    http_method_names = ["get"]

    @extend_schema(
        operation_id="getInitCheck",
        summary="Readiness probe",
        description="Get information about adcm backend initialization status",
        tags=["health"],
        responses=responses(success=(HTTP_200_OK, ReadinessSerializer), errors=(HTTP_503_SERVICE_UNAVAILABLE)),
    )
    @inject
    def get(
        self,
        _request: Request,
        secrets_backend: FromDishka[secrets.SecretsBackend],
        consul_backend: FromDishka[ConsulBackend | None],
        adcm_repo: FromDishka[ADCMRepoI],
        *_args,
        **_kwargs,
    ) -> Response:
        results = run_readiness_checks(secrets_backend, consul_backend, adcm_repo.get_uuid())
        ready = all(result.healthy for result in results)
        status_code = HTTP_200_OK if ready else HTTP_503_SERVICE_UNAVAILABLE
        data = {
            "status": "ok" if ready else "unavailable",
            "checks": {result.name: {"healthy": result.healthy, "detail": result.detail} for result in results},
        }
        serializer = ReadinessSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.data, status=status_code)


class LivenessView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    http_method_names = ["get"]

    @extend_schema(
        operation_id="getHealthCheck",
        summary="Liveness probe",
        description="Get information about adcm backend health.",
        tags=["health"],
        responses=responses(success=(HTTP_200_OK, LivenessSerializer)),
    )
    def get(self, *_, **__) -> Response:
        return Response(data={"status": "ok"}, status=HTTP_200_OK)
