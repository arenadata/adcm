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

from audit.alt.api import audit_update
from audit.alt.hooks import (
    extract_for_current_user,
)
from cm.errors import AdcmEx
from cm.services.adcm import retrieve_password_requirements
from core.rbac.operations import update_user_password
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rbac.models import User
from rbac.services.user import UserDB
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED

from api_v2.api_schema import ErrorSerializer
from api_v2.profile.serializers import ProfileSerializer, ProfileUpdateSerializer
from api_v2.utils.audit import profile_of_current_user, retrieve_user_password_groups
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    retrieve=extend_schema(
        operation_id="getCurrentUserInfo",
        description="Get current user information.",
        summary="GET current user information",
        responses={
            HTTP_200_OK: ProfileSerializer,
            HTTP_401_UNAUTHORIZED: ErrorSerializer,
        },
    ),
    partial_update=extend_schema(
        operation_id="patchCurrentUserInfo",
        description="Change current user password.",
        summary="PATCH current user information",
        responses={
            HTTP_200_OK: ProfileUpdateSerializer,
            HTTP_401_UNAUTHORIZED: ErrorSerializer,
        },
    ),
)
class ProfileView(RetrieveModelMixin, ADCMGenericViewSet):
    queryset = User.objects.exclude(username__in=settings.ADCM_HIDDEN_USERS)

    def get_object(self) -> User:
        return User.objects.get(user_ptr=self.request.user)

    def get_serializer_class(self) -> type[ProfileSerializer | ProfileUpdateSerializer]:
        if self.request.method in ("PATCH", "PUT"):
            return ProfileUpdateSerializer

        return ProfileSerializer

    @(
        audit_update(name="Profile updated", object_=profile_of_current_user).track_changes(
            before=(extract_for_current_user(func=retrieve_user_password_groups, section="previous"),),
            after=(extract_for_current_user(func=retrieve_user_password_groups, section="current"),),
        )
    )
    def partial_update(self, request, *_, **__):
        user = self.get_object()

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if not (
            (current_password := serializer.validated_data.get("current_password", ""))
            and user.check_password(raw_password=current_password)
        ):
            raise AdcmEx(code="USER_PASSWORD_CURRENT_PASSWORD_REQUIRED_ERROR")

        update_user_password(
            user_id=user.pk,
            new_password=serializer.validated_data["password"],
            db=UserDB,
            password_requirements=retrieve_password_requirements(),
        )

        return Response()
