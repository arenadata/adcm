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

from cm.errors import AdcmEx
from cm.models import ConcernItem, get_model_by_type
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.exceptions import PermissionDenied
from rest_framework.mixins import DestroyModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from api_v2.api_schema import ErrorSerializer
from api_v2.concern.serializers import ConcernSerializer
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    destroy=extend_schema(
        operation_id="deleteConcern",
        description="Remove non blocking concern",
        summary="Remove non-blocking concern",
        responses={HTTP_204_NO_CONTENT: None, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
)
class ConcernViewSet(PermissionListMixin, ADCMGenericViewSet, DestroyModelMixin):
    serializer_class = ConcernSerializer
    queryset = ConcernItem.objects.all()
    permission_required = []

    def destroy(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        filter_kwargs = {self.lookup_field: self.kwargs[self.lookup_field]}
        instance = get_object_or_404(
            self.filter_queryset(self.get_get_objects_for_user_kwargs(self.queryset)["klass"]), **filter_kwargs
        )

        owner_id, owner_type = instance.owner_id, instance.owner_type.model
        owner = get_model_by_type(owner_type).objects.get(pk=owner_id)

        self.check_delete_concern_permissions(instance, owner)

        if not instance.blocking:
            instance.delete()
        else:
            raise AdcmEx(code="CONCERNITEM_NOT_REMOVED")
        return Response(status=HTTP_204_NO_CONTENT)

    def check_delete_concern_permissions(self, instance, owner):
        owner_view_perm = f"cm.view_{owner.__class__.__name__.lower()}"
        instance_remove_permission = f"cm.delete_{instance.__class__.__name__.lower()}"

        has_owner_view_object_perms = self.request.user.has_perm(owner_view_perm, owner)
        has_owner_view_perms = self.request.user.has_perm(owner_view_perm)
        has_remove_perms = self.request.user.has_perm(perm=instance_remove_permission)

        if not (has_owner_view_object_perms or has_owner_view_perms) or not has_remove_perms:
            raise PermissionDenied()
