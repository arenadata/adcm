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
from api_v2.login.serializers import LoginSerializer
from cm.errors import AdcmEx
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User as AuthUser
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
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK


class BaseLoginView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer
    renderer_classes = [CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer]
    parser_classes = [CamelCaseJSONParser, CamelCaseMultiPartParser, CamelCaseFormParser]
    http_method_names = ["post"]

    def perform_login(self, request: Request) -> AuthUser:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(request=request, **serializer.validated_data)
        if user is None:
            raise AdcmEx(code="AUTH_ERROR")

        login(request=request, user=user, backend="django.contrib.auth.backends.ModelBackend")

        return user


class LoginView(BaseLoginView):
    def post(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        self.perform_login(request=request)
        return Response(status=HTTP_200_OK)
