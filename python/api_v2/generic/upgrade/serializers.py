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


from cm.models import Upgrade
from drf_spectacular.utils import extend_schema_field
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from api_v2.bundle.serializers import UpgradeBundleSerializer
from api_v2.generic.action.serializers import ActionConfigurationSerializer, HCMapRuleEntrySerializer


class UpgradeListSerializer(ModelSerializer):
    class Meta:
        model = Upgrade
        fields = ["id", "name", "display_name"]


class UpgradeRetrieveSerializer(UpgradeListSerializer):
    is_allow_to_terminate = SerializerMethodField()
    host_component_map_rules = SerializerMethodField()
    disclaimer = SerializerMethodField()
    configuration = SerializerMethodField()
    bundle = UpgradeBundleSerializer()

    class Meta:
        model = Upgrade
        fields = (
            "id",
            "name",
            "display_name",
            "is_allow_to_terminate",
            "host_component_map_rules",
            "configuration",
            "disclaimer",
            "bundle",
        )

    @staticmethod
    def get_disclaimer(instance: Upgrade) -> str:
        if instance.action:
            return instance.action.ui_options.get("disclaimer", "")

        return ""

    @staticmethod
    def get_is_allow_to_terminate(instance: Upgrade) -> bool:
        if instance.action:
            return instance.action.allow_to_terminate

        return False

    @extend_schema_field(field=HCMapRuleEntrySerializer(many=True))
    def get_host_component_map_rules(self, instance: Upgrade) -> list[dict]:
        if instance.action:
            return instance.action.hostcomponentmap

        return []

    @extend_schema_field(field=ActionConfigurationSerializer)
    def get_configuration(self, _: Upgrade) -> dict | None:
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
