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

from django.conf import settings
from djangorestframework_camel_case.parser import (
    CamelCaseFormParser,
    CamelCaseJSONParser,
    CamelCaseMultiPartParser,
)
from djangorestframework_camel_case.render import (
    CamelCaseBrowsableAPIRenderer,
    CamelCaseJSONRenderer,
)
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.viewsets import GenericViewSet


class APIRoot(APIRootView):
    permission_classes = (AllowAny,)
    api_root_dict = {
        "adcm-info": "adcm-info",
        "adcm": "adcm-detail",
        "clusters": "cluster-list",
        "audit": "audit:root",
        "bundles": "bundle-list",
        "hosts": "host-list",
        "hostproviders": "hostprovider-list",
        "prototypes": "prototype-list",
        "jobs": "joblog-list",
        "tasks": "tasklog-list",
        "rbac": "rbac:root",
    }


class CamelCaseGenericViewSet(GenericViewSet):
    parser_classes = [CamelCaseJSONParser, CamelCaseMultiPartParser, CamelCaseFormParser]
    renderer_classes = [CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer]


class CamelCaseModelViewSet(
    CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, ListModelMixin, CamelCaseGenericViewSet
):  # pylint: disable=too-many-ancestors
    pass


class CamelCaseReadOnlyModelViewSet(
    RetrieveModelMixin, ListModelMixin, CamelCaseGenericViewSet
):  # pylint: disable=too-many-ancestors
    pass


class ADCMInfo(GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, _) -> Response:
        return Response(data={"version": settings.ADCM_VERSION})
