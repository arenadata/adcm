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

from typing import Any

from api_v2.config.serializers import ConfigSerializerUI
from cm.adcm_config.config import get_action_variant, get_prototype_config
from cm.models import Cluster, HostProvider, PrototypeConfig, Upgrade
from rest_framework.serializers import (
    BooleanField,
    JSONField,
    ModelSerializer,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer


class UpgradeListSerializer(ModelSerializer):
    prototype_type = None
    is_license_accepted = SerializerMethodField()

    class Meta:
        model = Upgrade
        fields = ["id", "name", "display_name", "is_license_accepted"]

    @classmethod
    def get_is_license_accepted(cls, upgrade: Upgrade) -> bool:
        return upgrade.bundle.prototype_set.filter(type=cls.prototype_type).first().is_license_accepted


class ClusterUpgradeListSerializer(UpgradeListSerializer):
    prototype_type = "cluster"


class HostProviderUpgradeListSerializer(UpgradeListSerializer):
    prototype_type = "provider"


class UpgradeRetrieveSerializer(ModelSerializer):
    is_allow_to_terminate = SerializerMethodField()
    host_component_map_rules = SerializerMethodField()
    disclaimer = SerializerMethodField()
    config = SerializerMethodField()

    class Meta:
        model = Upgrade
        fields = ["is_allow_to_terminate", "host_component_map_rules", "disclaimer", "config"]

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

    @staticmethod
    def get_host_component_map_rules(instance: Upgrade) -> Any:
        if instance.action:
            return instance.action.hostcomponentmap

        return []

    def get_config(self, instance):
        if instance.action is None:
            return {"attr": {}, "config": []}

        if "cluster_id" in self.context:
            obj = Cluster.obj.get(pk=self.context["cluster_id"])
        elif "provider_id" in self.context:
            obj = HostProvider.obj.get(pk=self.context["provider_id"])
        else:
            obj = None

        action_conf = PrototypeConfig.objects.filter(
            prototype=instance.action.prototype,
            action=instance.action,
        ).order_by("id")
        *_, attr = get_prototype_config(instance.action.prototype, instance.action)
        if obj:
            get_action_variant(obj, action_conf)
        conf = ConfigSerializerUI(action_conf, many=True, context=self.context, read_only=True)
        return {"attr": attr, "config": conf.data}


class UpgradeRunSerializer(EmptySerializer):
    host_component_map = JSONField()
    config = JSONField()
    attr = JSONField()
    is_verbose = BooleanField()
