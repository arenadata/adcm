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

from api_v2.concern.serializers import ConcernSerializer
from api_v2.prototype.serializers import PrototypeRelatedSerializer
from cm.models import ADCM
from rest_framework.serializers import ModelSerializer


class AdcmSerializer(ModelSerializer):
    prototype = PrototypeRelatedSerializer(read_only=True)
    concerns = ConcernSerializer(read_only=True, many=True)

    class Meta:
        model = ADCM
        fields = ["id", "name", "state", "multi_state", "prototype", "concerns"]
