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

from guardian.mixins import PermissionListMixin
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.object_config.serializers import ObjectConfigSerializer
from cm.models import ObjectConfig


class ObjectConfigViewSet(
    PermissionListMixin, ReadOnlyModelViewSet
):  # pylint: disable=too-many-ancestors
    queryset = ObjectConfig.objects.all()
    serializer_class = ObjectConfigSerializer
    permission_classes = (DjangoObjectPermissions,)
    permission_required = ['cm.view_objectconfig']

    def get_queryset(self, *args, **kwargs):
        if self.request.user.has_perm('cm.view_settings_of_adcm'):
            return super().get_queryset(*args, **kwargs) | ObjectConfig.objects.filter(
                adcm__isnull=False
            )
        else:
            return super().get_queryset(*args, **kwargs).filter(adcm__isnull=True)
