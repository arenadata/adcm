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

from cm.models import Action
from rest_framework.serializers import (
    BooleanField,
    JSONField,
    ModelSerializer,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer


class ActionListSerializer(ModelSerializer):
    start_impossible_reason = SerializerMethodField()

    class Meta:
        model = Action
        fields = ["id", "name", "display_name", "start_impossible_reason"]

    def get_start_impossible_reason(self, action: Action) -> str | None:
        return action.get_start_impossible_reason(obj=self.context["obj"])


class ActionRetrieveSerializer(ModelSerializer):
    is_allow_to_terminate = BooleanField(source="allow_to_terminate")
    host_component_map_rules = JSONField(source="hostcomponentmap")
    disclaimer = SerializerMethodField()

    class Meta:
        model = Action
        fields = ["is_allow_to_terminate", "host_component_map_rules", "disclaimer"]

    @staticmethod
    def get_disclaimer(action: Action) -> str:
        return action.ui_options.get("disclaimer") or ""


class ActionRunSerializer(EmptySerializer):
    host_component_map = JSONField()
    config = JSONField()
    attr = JSONField()
    is_verbose = BooleanField()


class ActionNameSerializer(ModelSerializer):
    class Meta:
        model = Action
        fields = ["id", "name", "display_name"]
