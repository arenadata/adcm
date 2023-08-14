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

# pylint: disable=redefined-builtin

from api.action.serializers import ActionShort
from api.cluster.serializers import BindSerializer
from api.component.serializers import ComponentUISerializer
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.group_config.serializers import GroupConfigsHyperlinkedIdentityField
from api.serializers import StringListSerializer
from api.utils import CommonAPIURL, ObjectURL, check_obj
from cm.adcm_config.config import get_main_info
from cm.api import add_service_to_cluster, bind, multi_bind
from cm.errors import AdcmEx
from cm.models import (
    MAINTENANCE_MODE_BOTH_CASES_CHOICES,
    Action,
    Cluster,
    ClusterObject,
    Prototype,
    ServiceComponent,
)
from cm.status_api import get_service_status
from django.db.utils import IntegrityError
from rest_framework.reverse import reverse
from rest_framework.serializers import (
    BooleanField,
    CharField,
    ChoiceField,
    HyperlinkedIdentityField,
    HyperlinkedRelatedField,
    IntegerField,
    JSONField,
    ModelSerializer,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer
from adcm.utils import filter_actions


class ServiceSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    cluster_id = IntegerField(required=True)
    name = CharField(read_only=True)
    display_name = CharField(read_only=True)
    state = CharField(read_only=True)
    prototype_id = IntegerField(required=True, help_text="id of service prototype")
    url = ObjectURL(read_only=True, view_name="v1:service-details")
    maintenance_mode = CharField(read_only=True)
    is_maintenance_mode_available = BooleanField(read_only=True)

    def to_representation(self, instance: ClusterObject) -> dict:
        data = super().to_representation(instance=instance)
        data["maintenance_mode"] = data["maintenance_mode"].upper()

        return data

    @staticmethod
    def validate_prototype_id(prototype_id):
        check_obj(Prototype, {"id": prototype_id, "type": "service"}, "PROTOTYPE_NOT_FOUND")

        return prototype_id

    def create(self, validated_data):
        try:
            cluster = check_obj(Cluster, validated_data["cluster_id"])
            prototype = check_obj(Prototype, validated_data["prototype_id"])
            return add_service_to_cluster(cluster, prototype)
        except IntegrityError:
            raise AdcmEx("SERVICE_CONFLICT") from None


class ServiceUISerializer(ServiceSerializer):
    action = CommonAPIURL(read_only=True, view_name="v1:object-action")
    name = CharField(read_only=True)
    version = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    status = SerializerMethodField()
    hostcomponent = HyperlinkedIdentityField(
        view_name="v1:host-component", lookup_field="cluster_id", lookup_url_kwarg="cluster_id"
    )

    @staticmethod
    def get_version(obj: ClusterObject) -> str:
        return obj.prototype.version

    @staticmethod
    def get_status(obj: ClusterObject) -> int:
        return get_service_status(obj)


class ClusterServiceSerializer(ServiceSerializer):
    cluster_id = IntegerField(read_only=True)

    def create(self, validated_data):
        try:
            cluster = check_obj(Cluster, self.context.get("cluster_id"))
            prototype = check_obj(Prototype, validated_data["prototype_id"])
            return add_service_to_cluster(cluster, prototype)
        except IntegrityError:
            raise AdcmEx("SERVICE_CONFLICT") from None


class ServiceDetailSerializer(ServiceSerializer):
    prototype_id = IntegerField(read_only=True)
    description = CharField(read_only=True)
    bundle_id = IntegerField(read_only=True)
    requires = JSONField(read_only=True)
    status = SerializerMethodField()
    monitoring = CharField(read_only=True)
    action = CommonAPIURL(read_only=True, view_name="v1:object-action")
    config = CommonAPIURL(read_only=True, view_name="v1:object-config")
    component = ObjectURL(read_only=True, view_name="v1:component")
    imports = ObjectURL(read_only=True, view_name="v1:service-import")
    bind = ObjectURL(read_only=True, view_name="v1:service-bind")
    prototype = HyperlinkedRelatedField(
        read_only=True,
        view_name="v1:service-prototype-detail",
        lookup_url_kwarg="prototype_pk",
    )
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    group_config = GroupConfigsHyperlinkedIdentityField(view_name="v1:group-config-list")

    @staticmethod
    def get_status(obj: ClusterObject) -> int:
        return get_service_status(obj)


class ServiceDetailUISerializer(ServiceDetailSerializer):
    actions = SerializerMethodField()
    components = SerializerMethodField()
    name = CharField(read_only=True)
    version = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = SerializerMethodField()
    hostcomponent = HyperlinkedIdentityField(
        view_name="v1:host-component", lookup_field="cluster_id", lookup_url_kwarg="cluster_id"
    )

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context["object"] = obj
        self.context["service_id"] = obj.id
        actions = filter_actions(obj, act_set)
        acts = ActionShort(actions, many=True, context=self.context)

        return acts.data

    def get_components(self, obj):
        comps = ServiceComponent.objects.filter(service=obj, cluster=obj.cluster)

        return ComponentUISerializer(comps, many=True, context=self.context).data

    @staticmethod
    def get_version(obj: ClusterObject) -> str:
        return obj.prototype.version

    @staticmethod
    def get_main_info(obj: ClusterObject) -> str | None:
        return get_main_info(obj)


class ImportPostSerializer(EmptySerializer):
    bind = JSONField()

    def create(self, validated_data):
        binds = validated_data.get("bind")
        service = self.context.get("service")
        cluster = self.context.get("cluster")

        return multi_bind(cluster, service, binds)


class ServiceBindUrlFields(HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, _format):
        kwargs = {"service_id": obj.service.id, "bind_id": obj.id}

        return reverse(view_name, kwargs=kwargs, request=request, format=_format)


class ServiceBindSerializer(BindSerializer):
    url = ServiceBindUrlFields(read_only=True, view_name="v1:service-bind-details")


class ServiceBindPostSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    export_cluster_id = IntegerField()
    export_service_id = IntegerField(required=False)
    export_cluster_name = CharField(read_only=True)
    export_service_name = CharField(read_only=True)
    export_cluster_prototype_name = CharField(read_only=True)

    def create(self, validated_data):
        export_cluster = check_obj(Cluster, validated_data.get("export_cluster_id"))

        return bind(
            validated_data.get("cluster"),
            validated_data.get("service"),
            export_cluster,
            validated_data.get("export_service_id"),
        )


class ServiceStatusSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(read_only=True)
    status = SerializerMethodField()

    @staticmethod
    def get_status(obj):
        return get_service_status(obj)


class ServiceChangeMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=MAINTENANCE_MODE_BOTH_CASES_CHOICES)

    class Meta:
        model = ClusterObject
        fields = ("maintenance_mode",)

    @staticmethod
    def validate_maintenance_mode(value: str) -> str:
        return value.lower()

    def to_representation(self, instance: ClusterObject) -> dict:
        data = super().to_representation(instance=instance)
        data["maintenance_mode"] = data["maintenance_mode"].upper()

        return data


class ServiceAuditSerializer(ModelSerializer):
    class Meta:
        model = ClusterObject
        fields = ("maintenance_mode",)

    def to_representation(self, instance) -> dict:
        data = super().to_representation(instance=instance)
        data["maintenance_mode"] = data["maintenance_mode"].upper()

        return data
