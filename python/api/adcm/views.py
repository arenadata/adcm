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

from cm.models import ADCM
from api.api_views import DetailViewRO, ListView
from . import serializers


class AdcmList(ListView):
    """
    get:
    List adcm object
    """
    queryset = ADCM.objects.all()
    serializer_class = serializers.AdcmSerializer
    serializer_class_ui = serializers.AdcmDetailSerializer


class AdcmDetail(DetailViewRO):
    """
    get:
    Show adcm object
    """
    queryset = ADCM.objects.all()
    serializer_class = serializers.AdcmDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'adcm_id'
    error_code = 'ADCM_NOT_FOUND'
