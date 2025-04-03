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

from adcm import settings
from adcm.serializers import EmptySerializer
from cm.models import Cluster, Component, Host, MaintenanceMode, Provider
from cm.validators import HostUniqueValidator, StartMidEndValidator
from drf_spectacular.utils import extend_schema_field
from rest_framework.serializers import (
    CharField,
    ChoiceField,
    IntegerField,
    ListSerializer,
    ModelSerializer,
    SerializerMethodField,
)

from api_v2.concern.serializers import ConcernSerializer
from api_v2.prototype.serializers import PrototypeRelatedSerializer
from api_v2.serializers import WithStatusSerializer


class ProviderParentSerializer(ModelSerializer):
    class Meta:
        model = Provider
        fields = ["id", "name", "display_name"]


class HostClusterSerializer(ModelSerializer):
    class Meta:
        model = Cluster
        fields = ["id", "name"]


class HCComponentNameSerializer(ModelSerializer):
    name = CharField()  # schema warning helper
    display_name = CharField()  # schema warning helper

    class Meta:
        model = Component
        fields = ["id", "name", "display_name"]


class HostSerializer(WithStatusSerializer):
    hostprovider = ProviderParentSerializer(source="provider")
    prototype = PrototypeRelatedSerializer()
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
            "description",
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
    @extend_schema_field(field=HCComponentNameSerializer(many=True))
    def get_components(instance: Host) -> list[dict]:
        return HCComponentNameSerializer(
            instance=[hc.component for hc in instance.hostcomponent_set.all()], many=True
        ).data


class HostUpdateSerializer(ModelSerializer):
    name = CharField(
        max_length=253,
        help_text="fully qualified domain name",
        required=True,
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
        fields = ["name", "description"]


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


class HostAddSerializer(EmptySerializer):
    host_id = IntegerField()


class HostMappingSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=(MaintenanceMode.ON.value, MaintenanceMode.OFF.value))

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


class HostAuditSerializer(ModelSerializer):
    class Meta:
        model = Host
        fields = ["fqdn", "description", "maintenance_mode"]


class ManyHostAddSerializer(ListSerializer):
    child = HostAddSerializer()
