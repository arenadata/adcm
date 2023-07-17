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

from cm.models import ConcernItem
from rest_framework.serializers import (
    BooleanField,
    ModelSerializer,
    SerializerMethodField,
)


class ConcernSerializer(ModelSerializer):
    is_blocking = BooleanField(source="blocking")
    reason = SerializerMethodField()

    class Meta:
        model = ConcernItem
        fields = (
            "id",
            "reason",
            "is_blocking",
        )

    @staticmethod
    def get_reason(instance: ConcernItem) -> dict:
        reason = instance.reason

        if "source" in reason["placeholder"]:
            ids = reason["placeholder"]["source"].pop("ids")
            reason["placeholder"]["source"]["id"] = ids[reason["placeholder"]["source"]["type"]]

        if "target" in reason["placeholder"] and reason["placeholder"]["target"]["type"] != "prototype":
            ids = reason["placeholder"]["target"].pop("ids")
            reason["placeholder"]["target"]["id"] = ids[reason["placeholder"]["target"]["type"]]

        if "job" in reason["placeholder"]:
            ids = reason["placeholder"]["job"].pop("ids")
            reason["placeholder"]["job"]["id"] = ids

        return reason
