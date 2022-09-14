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

from rest_framework import permissions
from rest_framework.response import Response

from api.adcm.serializers import (
    AdcmDetailSerializer,
    AdcmDetailUISerializer,
    AdcmSerializer,
)
from api.base_view import DetailView, GenericUIView
from cm.models import ADCM


class AdcmList(GenericUIView):
    """
    get:
    List adcm object
    """

    queryset = ADCM.objects.all()
    serializer_class = AdcmSerializer
    serializer_class_ui = AdcmDetailUISerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        obj = self.get_queryset()
        serializer = self.get_serializer(obj, many=True)
        return Response(serializer.data)


class AdcmDetail(DetailView):
    """
    get:
    Show adcm object
    """

    queryset = ADCM.objects.all()
    serializer_class = AdcmDetailSerializer
    serializer_class_ui = AdcmDetailUISerializer
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'
    lookup_url_kwarg = 'adcm_id'
    error_code = 'ADCM_NOT_FOUND'
