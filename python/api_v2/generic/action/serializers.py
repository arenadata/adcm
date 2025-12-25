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

from adcm.serializers import EmptySerializer
from cm.legacy.services.action_process import repo
from cm.models import Action
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import CharField, ChoiceField, IntegerField
from rest_framework.serializers import (
    BooleanField,
    DictField,
    ModelSerializer,
    SerializerMethodField,
)

from api_v2.generic.action.process.serializers import ProcessShortSerializer


class ActionListSerializer(ModelSerializer):
    start_impossible_reason = SerializerMethodField()

    class Meta:
        model = Action
        fields = ["id", "name", "display_name", "start_impossible_reason"]

    def get_start_impossible_reason(self, action: Action) -> str | None:
        return action.get_start_impossible_reason(obj=self.context["obj"])


class HCMapRuleEntrySerializer(EmptySerializer):
    action = ChoiceField(choices=("add", "remove"))
    service = CharField()
    component = CharField()


class ActionConfigurationSerializer(EmptySerializer):
    config_schema = DictField()
    config = DictField()
    adcm_meta = DictField()


class ActionRetrieveSerializer(ActionListSerializer):
    is_allow_to_terminate = BooleanField(source="allow_to_terminate")
    host_component_map_rules = SerializerMethodField()
    disclaimer = SerializerMethodField()
    configuration = SerializerMethodField()
    processes = SerializerMethodField()

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
            "processes",
        ]

    @staticmethod
    def get_disclaimer(action: Action) -> str:
        return action.ui_options.get("disclaimer", "")

    @extend_schema_field(field=HCMapRuleEntrySerializer(many=True))
    def get_host_component_map_rules(self, action: Action) -> list[dict]:
        return action.hostcomponentmap

    @extend_schema_field(field=ActionConfigurationSerializer)
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

    @extend_schema_field(field=ProcessShortSerializer(many=True))
    def get_processes(self, _: Action) -> list[dict] | None:
        processes = self.context.get("processes")
        if processes is None:
            return None
        if not processes:
            return []

        serialized = []
        for process in processes:
            context = {
                "process_id": process.pk,
                "step_names_id_map": repo.retrieve_step_names_id_state_map(process_id=process.pk),
            }
            serialized.append(ProcessShortSerializer(process, context=context).data)

        return serialized


class HostComponentEntry(EmptySerializer):
    host_id = IntegerField()
    component_id = IntegerField()


class ActionRunConfiguration(EmptySerializer):
    config = DictField(allow_empty=True)
    adcm_meta = DictField(allow_empty=True)


class UpgradeRunSerializer(EmptySerializer):
    host_component_map = HostComponentEntry(many=True, default=list)
    configuration = ActionRunConfiguration(required=False, default=None, allow_null=True)
    is_verbose = BooleanField(required=False, default=False)


class ProcessIdSerializer(EmptySerializer):
    id = IntegerField()


class ActionRunSerializer(UpgradeRunSerializer):
    should_block_object = BooleanField(required=False, default=True, initial=True)
    process = ProcessIdSerializer(required=False, default=None, allow_null=True, initial=None)
    description = CharField(max_length=255, allow_blank=True, required=False, default="")


class ActionNameSerializer(ModelSerializer):
    class Meta:
        model = Action
        fields = ["id", "name", "display_name"]
