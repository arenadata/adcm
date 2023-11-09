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
from api_v2.profile.serializers import ProfileSerializer, ProfileUpdateSerializer
from audit.utils import audit
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
from rbac.models import User
from rbac.services.user import update_user
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response

from adcm.permissions import DjangoModelPermissionsAudit


class ProfileView(RetrieveUpdateAPIView):
    permission_classes = (DjangoModelPermissionsAudit,)
    permission_required = ["rbac.view_user"]
    queryset = User.objects.exclude(username__in=settings.ADCM_HIDDEN_USERS)
    serializer_class = ProfileSerializer
    renderer_classes = [CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer]
    parser_classes = [CamelCaseJSONParser, CamelCaseMultiPartParser, CamelCaseFormParser]

    def get_object(self) -> User:
        return User.objects.get(user_ptr=self.request.user)

    def get_serializer_class(self) -> type[ProfileSerializer | ProfileUpdateSerializer]:
        if self.request.method in ("PATCH", "PUT"):
            return ProfileUpdateSerializer

        return super().get_serializer_class()

    @audit
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        user = update_user(
            user=instance,
            context_user=self.request.user,
            partial=True,
            **serializer.validated_data,
        )

        return Response(data=self.get_serializer(instance=user).data)
