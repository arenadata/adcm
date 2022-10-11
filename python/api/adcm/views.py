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

from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from api.adcm.serializers import (
    ADCMRetrieveSerializer,
    ADCMSerializer,
    ADCMUISerializer,
)
from api.base_view import GenericUIViewSet
from cm.models import ADCM


# pylint:disable-next=too-many-ancestors
class ADCMViewSet(ListModelMixin, RetrieveModelMixin, GenericUIViewSet):
    queryset = ADCM.objects.select_related("prototype").all()
    serializer_class = ADCMSerializer
    lookup_url_kwarg = "adcm_pk"

    def get_serializer_class(self):

        if self.is_for_ui():
            return ADCMUISerializer

        if self.action == "retrieve":
            return ADCMRetrieveSerializer

        return super().get_serializer_class()
