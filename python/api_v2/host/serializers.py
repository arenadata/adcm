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
from cm.models import Cluster, Host, HostComponent, HostProvider, MaintenanceMode
from cm.status_api import get_host_status
from cm.validators import HostUniqueValidator, StartMidEndValidator
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    CharField,
    ChoiceField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    SerializerMethodField,
)

from adcm import settings
from adcm.permissions import VIEW_CLUSTER_PERM, VIEW_PROVIDER_PERM


class HostProviderSerializer(ModelSerializer):
    class Meta:
        model = HostProvider
        fields = ["id", "name"]


class HostClusterSerializer(ModelSerializer):
    class Meta:
        model = Cluster
        fields = ["id", "name"]


class HostComponentSerializer(ModelSerializer):
    name = CharField(source="component.name")
    display_name = CharField(source="component.display_name")

    class Meta:
        model = HostComponent
        fields = ["id", "name", "display_name"]


class HostSerializer(ModelSerializer):
    status = SerializerMethodField()
    provider = HostProviderSerializer()
    concerns = ConcernSerializer(many=True)
    fqdn = CharField(
        max_length=253,
        help_text="fully qualified domain name",
        validators=[
            HostUniqueValidator(queryset=Host.objects.all()),
            StartMidEndValidator(
                start=settings.ALLOWED_HOST_FQDN_START_CHARS,
                mid=settings.ALLOWED_HOST_FQDN_MID_END_CHARS,
                end=settings.ALLOWED_HOST_FQDN_MID_END_CHARS,
                err_code="BAD_REQUEST",
                err_msg="Wrong FQDN.",
            ),
        ],
    )

    class Meta:
        model = Host
        fields = [
            "id",
            "fqdn",
            "state",
            "status",
            "provider",
            "concerns",
            "is_maintenance_mode_available",
            "maintenance_mode",
        ]

    @staticmethod
    def get_status(host: Host) -> int:
        return get_host_status(host=host)


class HostUpdateSerializer(ModelSerializer):
    fqdn = CharField(
        max_length=253,
        help_text="fully qualified domain name",
        validators=[
            HostUniqueValidator(queryset=Host.objects.all()),
            StartMidEndValidator(
                start=settings.ALLOWED_HOST_FQDN_START_CHARS,
                mid=settings.ALLOWED_HOST_FQDN_MID_END_CHARS,
                end=settings.ALLOWED_HOST_FQDN_MID_END_CHARS,
                err_code="BAD_REQUEST",
                err_msg="Wrong FQDN.",
            ),
        ],
    )

    class Meta:
        model = Host
        fields = ["fqdn", "cluster"]
        extra_kwargs = {"fqdn": {"allow_null": True}, "cluster": {"allow_null": True}}

    def validate_cluster(self, cluster):
        if not cluster:
            return cluster

        if not self.context["request"].user.has_perm(perm=VIEW_CLUSTER_PERM, obj=cluster):
            raise ValidationError("Current user has no permission to view this cluster")
        if not self.context["request"].user.has_perm(perm="cm.map_host_to_cluster", obj=cluster):
            raise ValidationError("Current user has no permission to map host to this cluster")

        return cluster


class HostCreateSerializer(HostUpdateSerializer):
    class Meta:
        model = Host
        fields = ["provider", "fqdn", "cluster"]
        extra_kwargs = {"fqdn": {"allow_null": False}}

    def validate_provider(self, provider):
        if not provider:
            raise ValidationError("Missing required field provider")

        if not self.context["request"].user.has_perm(perm=VIEW_PROVIDER_PERM, obj=provider):
            raise ValidationError("Current user has no permission to view this provider")

        return provider


class ClusterHostSerializer(HostSerializer):
    components = HostComponentSerializer(source="hostcomponent_set", many=True)

    class Meta:
        model = Host
        fields = [*HostSerializer.Meta.fields, "components"]


class ClusterHostCreateSerializer(ModelSerializer):
    hosts = PrimaryKeyRelatedField(
        queryset=Host.objects.select_related("cluster").filter(cluster__isnull=True), many=True
    )

    class Meta:
        model = Host
        fields = ["hosts", "fqdn"]
        extra_kwargs = {"fqdn": {"read_only": True}}


class HostMappingSerializer(ModelSerializer):
    class Meta:
        model = Host
        fields = ["id", "name", "is_maintenance_mode_available", "maintenance_mode"]


class HostChangeMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=(MaintenanceMode.ON.value, MaintenanceMode.OFF.value))

    class Meta:
        model = Host
        fields = ["maintenance_mode"]


class HostShortSerializer(ModelSerializer):
    class Meta:
        model = Host
        fields = ["id", "fqdn"]


class HostGroupConfigSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(queryset=Host.objects.all())

    class Meta:
        model = Host
        fields = ["id", "name"]
        extra_kwargs = {"name": {"read_only": True}}
