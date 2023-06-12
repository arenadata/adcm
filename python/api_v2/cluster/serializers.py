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

from api_v2.concern.serializers import ConcernSerializer
from cm.adcm_config.config import get_main_info
from cm.models import Cluster, HostComponent, Prototype
from cm.status_api import get_obj_status
from cm.upgrade import get_upgrade
from rest_framework.serializers import (
    BooleanField,
    CharField,
    ModelSerializer,
    SerializerMethodField,
)

from adcm.utils import get_requires


class ClusterSerializer(ModelSerializer):
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
    def get_status(cluster: Cluster) -> str:
        return get_obj_status(obj=cluster)

    @staticmethod
    def get_is_upgradable(cluster: Cluster) -> bool:
        return bool(get_upgrade(obj=cluster))

    @staticmethod
    def get_main_info(cluster: Cluster) -> str | None:
        return get_main_info(obj=cluster)


class ClusterCreateSerializer(ModelSerializer):
    class Meta:
        model = Cluster
        fields = ["prototype", "name", "description"]


class ClusterUpdateSerializer(ModelSerializer):
    class Meta:
        model = Cluster
        fields = ["name"]


class ServicePrototypeSerializer(ModelSerializer):
    is_required = BooleanField(source="required")
    depend_on = SerializerMethodField()

    class Meta:
        model = Prototype
        fields = ["id", "name", "display_name", "version", "is_required", "depend_on", "is_license_accepted"]

    @staticmethod
    def get_depend_on(prototype: Prototype) -> list[dict[str, list[dict[str, Any]] | Any]] | None:
        return get_requires(prototype=prototype)


class HostComponentListSerializer(ModelSerializer):
    class Meta:
        model = HostComponent
        fields = ["service", "host", "component", "cluster"]


class HostComponentPostSerializer(ModelSerializer):
    class Meta:
        model = HostComponent
        fields = ["service", "host", "component", "cluster"]
