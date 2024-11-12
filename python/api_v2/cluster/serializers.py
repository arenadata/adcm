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
from cm.adcm_config.config import get_main_info
from cm.errors import AdcmEx
from cm.models import (
    AnsibleConfig,
    Cluster,
    Component,
    Host,
    HostComponent,
    MaintenanceMode,
    Prototype,
    Service,
)
from cm.upgrade import get_upgrade
from cm.validators import ClusterUniqueValidator, StartMidEndValidator
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import DictField
from rest_framework.serializers import (
    BooleanField,
    CharField,
    ChoiceField,
    IntegerField,
    ListField,
    ModelSerializer,
    SerializerMethodField,
)
from rest_framework.status import HTTP_409_CONFLICT

from api_v2.concern.serializers import ConcernSerializer
from api_v2.prototype.serializers import LicenseSerializer, PrototypeRelatedSerializer
from api_v2.prototype.utils import get_license_text
from api_v2.serializers import DependOnSerializer, WithStatusSerializer


class ClusterSerializer(WithStatusSerializer):
    prototype = PrototypeRelatedSerializer()
    concerns = ConcernSerializer(many=True, read_only=True)
    is_upgradable = SerializerMethodField()
    main_info = SerializerMethodField()

    class Meta:
        model = Cluster
        fields = [
            "id",
            "name",
            "description",
            "state",
            "multi_state",
            "status",
            "prototype",
            "description",
            "concerns",
            "is_upgradable",
            "main_info",
        ]

    @staticmethod
    def get_is_upgradable(cluster: Cluster) -> bool:
        return bool(get_upgrade(obj=cluster))

    @staticmethod
    def get_main_info(cluster: Cluster) -> str | None:
        return get_main_info(obj=cluster)


class ClusterRelatedSerializer(ModelSerializer):
    class Meta:
        model = Cluster
        fields = ["id", "name"]


class ClusterCreateSerializer(EmptySerializer):
    prototype_id = IntegerField()
    name = CharField(
        min_length=2,
        max_length=150,
        trim_whitespace=False,
        validators=[
            ClusterUniqueValidator(queryset=Cluster.objects.all()),
            StartMidEndValidator(
                start=settings.ALLOWED_CLUSTER_NAME_START_END_CHARS,
                mid=settings.ALLOWED_CLUSTER_NAME_MID_CHARS,
                end=settings.ALLOWED_CLUSTER_NAME_START_END_CHARS,
                err_code="BAD_REQUEST",
                err_msg="Wrong cluster name.",
            ),
        ],
    )
    description = CharField(required=False, allow_blank=True, default="")


class ClusterUpdateSerializer(ModelSerializer):
    name = CharField(
        min_length=2,
        max_length=150,
        trim_whitespace=False,
        validators=[
            ClusterUniqueValidator(queryset=Cluster.objects.all()),
            StartMidEndValidator(
                start=settings.ALLOWED_CLUSTER_NAME_START_END_CHARS,
                mid=settings.ALLOWED_CLUSTER_NAME_MID_CHARS,
                end=settings.ALLOWED_CLUSTER_NAME_START_END_CHARS,
                err_code="BAD_REQUEST",
                err_msg="Wrong cluster name.",
            ),
        ],
        required=False,
        help_text="Cluster name",
    )

    class Meta:
        model = Cluster
        fields = ["name", "description"]


class ClusterAuditSerializer(ModelSerializer):
    name = CharField(max_length=80, required=False)

    class Meta:
        model = Cluster
        fields = ("name", "description")


class ServiceNameSerializer(ModelSerializer):
    prototype = PrototypeRelatedSerializer(read_only=True)

    class Meta:
        model = Service
        fields = ["id", "name", "display_name", "state", "prototype"]


class ServicePrototypeSerializer(ModelSerializer):
    is_required = BooleanField(source="required")
    depend_on = SerializerMethodField()
    license = SerializerMethodField()

    class Meta:
        model = Prototype
        fields = ["id", "name", "display_name", "version", "is_required", "depend_on", "license"]

    @extend_schema_field(field=DependOnSerializer(many=True))
    def get_depend_on(self, prototype: Prototype) -> list[dict] | None:
        return self.context["depend_on"].get(prototype.id)

    @staticmethod
    @extend_schema_field(field=LicenseSerializer)
    def get_license(prototype: Prototype) -> dict:
        return {
            "status": prototype.license,
            "text": get_license_text(
                license_path=prototype.license_path,
                bundle_hash=prototype.bundle.hash,
            ),
        }


class SetMappingSerializer(EmptySerializer):
    host_id = IntegerField()
    component_id = IntegerField()


class MappingSerializer(ModelSerializer):
    host_id = IntegerField()
    component_id = IntegerField()

    class Meta:
        model = HostComponent
        fields = ["id", "host_id", "component_id"]
        extra_kwargs = {"id": {"read_only": True}}


class RelatedComponentStatusSerializer(WithStatusSerializer):
    class Meta:
        model = Component
        fields = ["id", "name", "display_name", "status"]


class RelatedServicesStatusesSerializer(WithStatusSerializer):
    components = RelatedComponentStatusSerializer(many=True)

    class Meta:
        model = Service
        fields = ["id", "name", "display_name", "status", "components"]


class RelatedHostsStatusesSerializer(WithStatusSerializer):
    class Meta:
        model = Host
        fields = ["id", "name", "status"]


class ClusterStatusSerializer(WithStatusSerializer):
    class Meta:
        model = Cluster
        fields = ["id", "name", "state", "status"]


class AnsibleConfigUpdateSerializer(EmptySerializer):
    config = DictField(write_only=True)

    @staticmethod
    def validate_config(value: dict) -> dict:
        # required to raise here AdcmEx directly,
        # because subclassing ValidationError with status_code override is no help
        # because Serializer handler will raise vanila ValidationError anyway

        if set(value) != {"defaults"}:
            raise AdcmEx(
                code="CONFIG_KEY_ERROR", msg="Only `defaults` section can be modified", http_code=HTTP_409_CONFLICT
            )

        defaults = value["defaults"]

        if set(defaults or ()) != {"forks"}:
            raise AdcmEx(
                code="CONFIG_KEY_ERROR",
                msg="Only `defaults.forks` parameter can be modified",
                http_code=HTTP_409_CONFLICT,
            )

        if not isinstance(defaults["forks"], int) or defaults["forks"] < 1:
            raise AdcmEx(
                code="CONFIG_VALUE_ERROR",
                msg="`defaults.forks` parameter must be an integer greater than 0",
                http_code=HTTP_409_CONFLICT,
            )

        defaults["forks"] = str(defaults["forks"])
        value["defaults"] = defaults

        return value


class AnsibleConfigRetrieveSerializer(ModelSerializer):
    config = DictField(source="value", read_only=True)
    adcm_meta = SerializerMethodField(read_only=True)

    class Meta:
        model = AnsibleConfig
        fields = ["config", "adcm_meta"]

    def get_adcm_meta(self, instance: AnsibleConfig) -> dict:  # noqa: ARG002
        return {}

    def to_representation(self, instance: AnsibleConfig) -> dict:
        data = super().to_representation(instance=instance)
        data["config"]["defaults"]["forks"] = int(data["config"]["defaults"]["forks"])

        return data


class RelatedHostComponentsStatusSerializer(WithStatusSerializer):
    id = IntegerField(source="component.id")
    name = CharField(source="component.name")
    display_name = CharField(source="component.display_name")

    class Meta:
        model = HostComponent
        fields = ["id", "name", "display_name", "status"]


class ClusterHostStatusSerializer(EmptySerializer):
    host_components = RelatedHostComponentsStatusSerializer(many=True, source="hostcomponent_set")

    class Meta:
        model = Host
        fields = ["host_components"]


class ComponentMappingSerializer(ModelSerializer):
    service = ServiceNameSerializer(read_only=True)
    depend_on = SerializerMethodField()
    constraints = ListField(source="constraint")
    prototype = PrototypeRelatedSerializer(read_only=True)
    maintenance_mode = SerializerMethodField()
    is_maintenance_mode_available = SerializerMethodField()

    class Meta:
        model = Component
        fields = [
            "id",
            "name",
            "display_name",
            "is_maintenance_mode_available",
            "maintenance_mode",
            "constraints",
            "prototype",
            "depend_on",
            "service",
        ]

    @extend_schema_field(field=DependOnSerializer(many=True))
    def get_depend_on(self, instance: Component) -> list[dict] | None:
        return self.context["depend_on"].get(instance.id)

    @extend_schema_field(field=ChoiceField(choices=(MaintenanceMode.ON.value, MaintenanceMode.OFF.value)))
    def get_maintenance_mode(self, instance: Component):
        return self.context["mm"].components.get(instance.id, MaintenanceMode.OFF).value

    @extend_schema_field(field=BooleanField())
    def get_is_maintenance_mode_available(self, _instance: Component):
        return self.context["is_mm_available"]
