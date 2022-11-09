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

from adwp_base.errors import AdwpEx
from guardian.mixins import PermissionListMixin
from rest_framework.status import HTTP_405_METHOD_NOT_ALLOWED
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import DjangoModelPermissionsAudit
from audit.utils import audit
from rbac import models
from rbac.endpoints.user.serializers import UserSerializer


class UserViewSet(PermissionListMixin, ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = models.User.objects.all()
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
            raise AdwpEx(
                "USER_DELETE_ERROR",
                msg="Built-in user could not be deleted",
                http_code=HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().destroy(request, args, kwargs)
