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

from adcm.permissions import DjangoModelPermissionsAudit
from audit.utils import audit
from cm.errors import raise_adcm_ex
from guardian.mixins import PermissionListMixin
from rbac.models import User
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.schemas.coreapi import AutoSchema
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ModelViewSet

from api.rbac.user.serializers import UserSerializer


class UserViewSet(PermissionListMixin, ModelViewSet):
    queryset = User.objects.prefetch_related("groups").all()
    serializer_class = UserSerializer
    permission_classes = (DjangoModelPermissionsAudit,)
    permission_required = ["rbac.view_user"]
    filterset_fields = (
        "id",
        "username",
        "first_name",
        "last_name",
        "email",
        "is_superuser",
        "built_in",
        "is_active",
        "type",
    )
    ordering_fields = ("id", "username", "first_name", "last_name", "email", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email")
    schema = AutoSchema()

    @audit
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @audit
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @audit
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.built_in:
            raise_adcm_ex("USER_DELETE_ERROR")

        return super().destroy(request, args, kwargs)

    @audit
    @action(methods=["post"], detail=True)
    def reset_failed_login_attempts(self, request: Request, pk: int) -> Response:
        if not request.user.is_superuser:
            return Response(data={"error": "Only superuser can reset login attempts."}, status=HTTP_400_BAD_REQUEST)

        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response(data={"error": f"User with ID {pk} was not found."}, status=HTTP_400_BAD_REQUEST)

        user.failed_login_attempts = 0
        user.blocked_at = None
        user.save(update_fields=["failed_login_attempts", "blocked_at"])

        return Response()
