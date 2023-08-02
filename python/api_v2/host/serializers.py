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
from api_v2.prototype.serializers import PrototypeRelatedSerializer
from cm.models import Cluster, Host, HostProvider, MaintenanceMode, ServiceComponent
from cm.status_api import get_obj_status
from cm.validators import HostUniqueValidator, StartMidEndValidator
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    CharField,
    ChoiceField,
    IntegerField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    SerializerMethodField,
)

from adcm import settings
from adcm.permissions import VIEW_CLUSTER_PERM
from adcm.serializers import EmptySerializer


class HostProviderSerializer(ModelSerializer):
    class Meta:
        model = HostProvider
        fields = ["id", "name", "display_name"]


class HostClusterSerializer(ModelSerializer):
    class Meta:
        model = Cluster
        fields = ["id", "name"]


class HCComponentNameSerializer(ModelSerializer):
    class Meta:
        model = ServiceComponent
        fields = ["id", "name", "display_name"]


class HostSerializer(ModelSerializer):
    status = SerializerMethodField()
    hostprovider = HostProviderSerializer(source="provider")
    prototype = PrototypeRelatedSerializer(read_only=True)
    concerns = ConcernSerializer(many=True)
    name = CharField(
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
        source="fqdn",
    )
    cluster = HostClusterSerializer(read_only=True)
    components = SerializerMethodField()

    class Meta:
        model = Host
        fields = [
            "id",
            "name",
            "state",
            "status",
            "hostprovider",
            "prototype",
            "concerns",
            "is_maintenance_mode_available",
            "maintenance_mode",
            "multi_state",
            "cluster",
            "components",
        ]

    @staticmethod
    def get_status(host: Host) -> str:
        return get_obj_status(obj=host)

    @staticmethod
    def get_components(instance: Host) -> list[dict]:
        return HCComponentNameSerializer(
            instance=[hc.component for hc in instance.hostcomponent_set.all()], many=True
        ).data


class HostUpdateSerializer(ModelSerializer):
    name = CharField(
        max_length=253,
        help_text="fully qualified domain name",
        required=False,
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
        source="fqdn",
    )

    class Meta:
        model = Host
        fields = ["name", "cluster"]
        extra_kwargs = {"cluster": {"required": False}}

    def validate_cluster(self, cluster):
        if not cluster:
            return cluster

        if not self.context["request"].user.has_perm(perm=VIEW_CLUSTER_PERM, obj=cluster):
            raise ValidationError("Current user has no permission to view this cluster")

        if not self.context["request"].user.has_perm(perm="cm.map_host_to_cluster", obj=cluster):
            raise ValidationError("Current user has no permission to map host to this cluster")

        return cluster


class HostCreateSerializer(EmptySerializer):
    name = CharField(
        allow_null=False,
        required=True,
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
        source="fqdn",
    )
    hostprovider_id = IntegerField(required=True)
    cluster_id = IntegerField(required=False)


class ClusterHostCreateSerializer(EmptySerializer):
    host_id = IntegerField()


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
    name = CharField(source="fqdn")

    class Meta:
        model = Host
        fields = ["id", "name"]


class HostGroupConfigSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(queryset=Host.objects.all())

    class Meta:
        model = Host
        fields = ["id", "name"]
        extra_kwargs = {"name": {"read_only": True}}
