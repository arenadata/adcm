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

from cm.errors import raise_adcm_ex
from rest_framework.fields import JSONField

from adcm.serializers import EmptySerializer


class ImportPostSerializer(EmptySerializer):
    bind = JSONField()

    @staticmethod
    def validate_bind(bind):
        if not isinstance(bind, list):
            raise_adcm_ex(code="INVALID_INPUT", msg="bind field should be a list")

        for item in bind:
            if "cluster_id" not in item:
                raise_adcm_ex(code="INVALID_INPUT", msg="'cluster_id' sub-field is required")

        return bind
