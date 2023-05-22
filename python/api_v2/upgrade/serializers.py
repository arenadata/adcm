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
from rest_framework.serializers import (
    BooleanField,
    JSONField,
    ModelSerializer,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer


class UpgradeListSerializer(ModelSerializer):
    is_license_accepted = SerializerMethodField()

    class Meta:
        model = Upgrade
        fields = ["id", "name", "display_name", "is_license_accepted"]

    @staticmethod
    def get_is_license_accepted(upgrade: Upgrade) -> bool:
        return upgrade.bundle.prototype_set.filter(type="cluster").first().is_license_accepted


class UpgradeRetrieveSerializer(ModelSerializer):
    is_allow_to_terminate = BooleanField(source="action.allow_to_terminate")
    host_component_map_rules = JSONField(source="action.hostcomponentmap")
    disclaimer = SerializerMethodField()

    class Meta:
        model = Upgrade
        fields = ["is_allow_to_terminate", "host_component_map_rules", "disclaimer"]

    @staticmethod
    def get_disclaimer(upgrade: Upgrade) -> str:
        return upgrade.action.ui_options.get("disclaimer") or ""


class UpgradeRunSerializer(EmptySerializer):
    host_component_map = JSONField()
    config = JSONField()
    attr = JSONField()
    is_verbose = BooleanField()
