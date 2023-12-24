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
from rest_framework.fields import IntegerField
from rest_framework.serializers import (
    BooleanField,
    DictField,
    JSONField,
    ListSerializer,
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


class ActionRetrieveSerializer(ActionListSerializer):
    is_allow_to_terminate = BooleanField(source="allow_to_terminate")
    host_component_map_rules = JSONField(source="hostcomponentmap")
    disclaimer = SerializerMethodField()
    configuration = SerializerMethodField()

    class Meta:
        model = Action
        fields = [
            "id",
            "name",
            "display_name",
            "start_impossible_reason",
            "is_allow_to_terminate",
            "host_component_map_rules",
            "disclaimer",
            "configuration",
        ]

    @staticmethod
    def get_disclaimer(action: Action) -> str:
        return action.ui_options.get("disclaimer", "")

    def get_configuration(self, _: Action) -> dict | None:
        if (
            self.context["config_schema"] is None
            and self.context["config"] is None
            and self.context["adcm_meta"] is None
        ):
            return None

        return {
            "config_schema": self.context["config_schema"],
            "config": self.context["config"],
            "adcm_meta": self.context["adcm_meta"],
        }


class HostComponentEntry(EmptySerializer):
    host_id = IntegerField()
    component_id = IntegerField()


class ActionConfiguration(EmptySerializer):
    config = DictField(allow_empty=True)
    adcm_meta = DictField(allow_empty=True)


class ActionRunSerializer(EmptySerializer):
    host_component_map = ListSerializer(child=HostComponentEntry(), required=False, default=[])
    configuration = ActionConfiguration(required=False, default=None, allow_null=True)
    is_verbose = BooleanField(required=False, default=False)


class ActionNameSerializer(ModelSerializer):
    class Meta:
        model = Action
        fields = ["id", "name", "display_name"]
