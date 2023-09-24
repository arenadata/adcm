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

from api_v2.adcm.serializers import LoginSerializer, ProfileSerializer
from api_v2.config.views import ConfigLogViewSet
from cm.adcm_config.config import get_adcm_config
from cm.errors import AdcmEx
from cm.models import ADCM, ConfigLog
from django.contrib.auth import authenticate, login, logout
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
from rbac.models import User
from rbac.services.user import update_user
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from adcm.serializers import EmptySerializer


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
        _, adcm_auth_config = get_adcm_config(section="auth_policy")

        return Response(data={"auth_settings": adcm_auth_config})


class LogoutView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmptySerializer
    http_method_names = ["post"]
    parser_classes = [CamelCaseJSONParser, CamelCaseMultiPartParser, CamelCaseFormParser]
    renderer_classes = [CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer]

    def post(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        logout(request)

        return Response(status=HTTP_204_NO_CONTENT)


class TokenView(BaseLoginView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        user = self.perform_login(request=request)
        token, _ = Token.objects.get_or_create(user=user)

        return Response({"token": token.key})


class ProfileView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.all()
    serializer_class = ProfileSerializer
    renderer_classes = [CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer]
    parser_classes = [CamelCaseJSONParser, CamelCaseMultiPartParser, CamelCaseFormParser]

    def get_object(self) -> User:
        return User.objects.get(user_ptr=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        user = update_user(
            user=instance,
            context_user=self.request.user,
            partial=True,
            api_v2_behaviour=True,
            **serializer.validated_data,
        )

        return Response(data=self.get_serializer(instance=user).data)


class ADCMConfigView(ConfigLogViewSet):  # pylint: disable=too-many-ancestors
    def get_queryset(self, *args, **kwargs):
        return (
            ConfigLog.objects.select_related("obj_ref__adcm__prototype")
            .filter(obj_ref__adcm__isnull=False)
            .order_by("-pk")
        )

    def get_parent_object(self) -> ADCM | None:
        return ADCM.objects.first()
