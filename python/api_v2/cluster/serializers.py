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
from cm.adcm_config.config import get_main_info
from cm.models import Cluster
from cm.status_api import get_cluster_status
from cm.upgrade import get_upgrade
from rest_framework.serializers import CharField, ModelSerializer, SerializerMethodField


class ClusterGetSerializer(ModelSerializer):
    status = SerializerMethodField()
    prototype_name = CharField(source="prototype.name")
    prototype_version = CharField(source="prototype.version")
    concerns = ConcernSerializer(many=True, read_only=True)
    is_upgradable = SerializerMethodField()
    main_info = SerializerMethodField()

    class Meta:
        model = Cluster
        fields = [
            "id",
            "name",
            "state",
            "multi_state",
            "status",
            "prototype_name",
            "prototype_version",
            "description",
            "concerns",
            "is_upgradable",
            "main_info",
        ]

    @staticmethod
    def get_status(cluster: Cluster) -> int:
        return get_cluster_status(cluster=cluster)

    @staticmethod
    def get_is_upgradable(cluster: Cluster) -> bool:
        return bool(get_upgrade(obj=cluster))

    @staticmethod
    def get_main_info(cluster: Cluster) -> str | None:
        return get_main_info(obj=cluster)


class ClusterPostSerializer(ModelSerializer):
    class Meta:
        model = Cluster
        fields = ["prototype", "name", "description"]


class ClusterPatchSerializer(ModelSerializer):
    class Meta:
        model = Cluster
        fields = ["name"]
