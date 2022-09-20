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

from django.conf import settings
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    BooleanField,
    CharField,
    IntegerField,
    JSONField,
    ModelSerializer,
    Serializer,
    SerializerMethodField,
)
from rest_framework.validators import UniqueValidator

from adcm.serializers import EmptySerializer
from api.action.serializers import ActionShort
from api.component.serializers import ComponentDetailSerializer
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.group_config.serializers import GroupConfigsHyperlinkedIdentityField
from api.host.serializers import HostSerializer
from api.serializers import DoUpgradeSerializer, StringListSerializer
from api.utils import (
    CommonAPIURL,
    ObjectURL,
    UrlField,
    check_obj,
    filter_actions,
    get_upgradable_func,
    hlink,
)
from api.validators import RegexValidator
from cm.adcm_config import get_main_info
from cm.api import add_cluster, add_hc, bind, multi_bind
from cm.errors import AdcmEx
from cm.models import Action, Cluster, Host, Prototype, ServiceComponent, Upgrade
from cm.status_api import get_cluster_status, get_hc_status
from cm.upgrade import do_upgrade


def get_cluster_id(obj):
    if hasattr(obj.obj_ref, "clusterobject"):
        return obj.obj_ref.clusterobject.cluster.id
    else:
        return obj.obj_ref.cluster.id


class ClusterUniqueValidator(UniqueValidator):
    def __call__(self, value, serializer_field):
        try:
            super().__call__(value, serializer_field)
        except ValidationError as e:
            raise AdcmEx("CLUSTER_CONFLICT", f'Cluster with name "{value}" already exists') from e


class ClusterSerializer(Serializer):
    id = IntegerField(read_only=True)
    prototype_id = IntegerField(help_text="ID of Cluster type")
    name = CharField(
        help_text="Cluster name",
        validators=[
            ClusterUniqueValidator(queryset=Cluster.objects.all()),
            RegexValidator(
                regex=settings.REGEX_CLUSTER_NAME,
                code="WRONG_NAME",
                msg="Name `{value}` doesn't meets requirements",
            ),
        ],
    )
    description = CharField(help_text="Cluster description", required=False)
    state = CharField(read_only=True)
    before_upgrade = JSONField(read_only=True)
    url = hlink("cluster-details", "id", "cluster_id")

    @staticmethod
    def validate_prototype_id(prototype_id):
        return check_obj(Prototype, {"id": prototype_id, "type": "cluster"})

    def create(self, validated_data):
        return add_cluster(
            validated_data.get("prototype_id"),
            validated_data.get("name"),
            validated_data.get("description", ""),
        )

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.save()
        return instance


class ClusterDetailSerializer(ClusterSerializer):
    bundle_id = IntegerField(read_only=True)
    edition = CharField(read_only=True)
    license = CharField(read_only=True)
    action = CommonAPIURL(view_name="object-action")
    service = ObjectURL(view_name="service")
    host = ObjectURL(view_name="host")
    hostcomponent = hlink("host-component", "id", "cluster_id")
    status = SerializerMethodField()
    status_url = hlink("cluster-status", "id", "cluster_id")
    config = CommonAPIURL(view_name="object-config")
    serviceprototype = hlink("cluster-service-prototype", "id", "cluster_id")
    upgrade = hlink("cluster-upgrade", "id", "cluster_id")
    imports = hlink("cluster-import", "id", "cluster_id")
    bind = hlink("cluster-bind", "id", "cluster_id")
    prototype = hlink("cluster-type-details", "prototype_id", "prototype_id")
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    group_config = GroupConfigsHyperlinkedIdentityField(view_name="group-config-list")

    @staticmethod
    def get_status(obj):
        return get_cluster_status(obj)


class ClusterUpdateSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(
        max_length=80,
        validators=[
            ClusterUniqueValidator(queryset=Cluster.objects.all()),
            RegexValidator(
                regex=settings.REGEX_CLUSTER_NAME,
                code="WRONG_NAME",
                msg="Name `{value}` doesn't meets requirements",
            ),
        ],
        required=False,
        help_text="Cluster name",
    )
    description = CharField(required=False, help_text="Cluster description")

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.save()
        return instance


class ClusterUISerializer(ClusterDetailSerializer):
    actions = SerializerMethodField()
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    upgradable = SerializerMethodField()
    get_upgradable = get_upgradable_func
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context["object"] = obj
        self.context["cluster_id"] = obj.id
        actions = ActionShort(filter_actions(obj, act_set), many=True, context=self.context)
        return actions.data

    @staticmethod
    def get_prototype_version(obj):
        return obj.prototype.version

    @staticmethod
    def get_prototype_name(obj):
        return obj.prototype.name

    @staticmethod
    def get_prototype_display_name(obj):
        return obj.prototype.display_name

    @staticmethod
    def get_main_info(obj):
        return get_main_info(obj)


class StatusSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    component_id = IntegerField(read_only=True)
    service_id = IntegerField(read_only=True)
    state = CharField(read_only=True, required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["component"] = instance.component.prototype.name
        data["component_display_name"] = instance.component.prototype.display_name
        data["host"] = instance.host.fqdn
        data["service_name"] = instance.service.prototype.name
        data["service_display_name"] = instance.service.prototype.display_name
        data["service_version"] = instance.service.prototype.version
        data["monitoring"] = instance.component.prototype.monitoring
        status = get_hc_status(instance)
        data["status"] = status
        return data


class HostComponentSerializer(EmptySerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {
                "cluster_id": obj.cluster.id,
                "hs_id": obj.id,
            }

    id = IntegerField(read_only=True)
    host_id = IntegerField(help_text="host id")
    host = CharField(read_only=True)
    service_id = IntegerField()
    component = CharField(help_text="component name")
    component_id = IntegerField(read_only=True, help_text="component id")
    state = CharField(read_only=True, required=False)
    url = MyUrlField(read_only=True, view_name="host-comp-details")
    host_url = hlink("host-details", "host_id", "host_id")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["component"] = instance.component.prototype.name
        data["component_display_name"] = instance.component.prototype.display_name
        data["host"] = instance.host.fqdn
        data["service_name"] = instance.service.prototype.name
        data["service_display_name"] = instance.service.prototype.display_name
        data["service_version"] = instance.service.prototype.version
        return data


class HostComponentUISerializer(EmptySerializer):
    hc = HostComponentSerializer(many=True, read_only=True)
    host = SerializerMethodField()
    component = SerializerMethodField()

    def get_host(self, obj):
        hosts = Host.objects.filter(cluster=self.context.get("cluster"))
        return HostSerializer(hosts, many=True, context=self.context).data

    def get_component(self, obj):
        comps = ServiceComponent.objects.filter(cluster=self.context.get("cluster"))
        return HCComponentSerializer(comps, many=True, context=self.context).data


class HostComponentSaveSerializer(EmptySerializer):
    hc = JSONField()

    @staticmethod
    def validate_hc(hc):
        if not hc:
            raise AdcmEx("INVALID_INPUT", "hc field is required")
        if not isinstance(hc, list):
            raise AdcmEx("INVALID_INPUT", "hc field should be a list")
        for item in hc:
            for key in ("component_id", "host_id", "service_id"):
                if key not in item:
                    msg = '"{}" sub-field is required'
                    raise AdcmEx("INVALID_INPUT", msg.format(key))
        return hc

    def create(self, validated_data):
        hc = validated_data.get("hc")
        return add_hc(self.context.get("cluster"), hc)


class HCComponentSerializer(ComponentDetailSerializer):
    service_id = IntegerField(read_only=True)
    service_name = SerializerMethodField()
    service_display_name = SerializerMethodField()
    service_state = SerializerMethodField()
    requires = SerializerMethodField()

    @staticmethod
    def get_service_state(obj):
        return obj.service.state

    @staticmethod
    def get_service_name(obj):
        return obj.service.prototype.name

    @staticmethod
    def get_service_display_name(obj):
        return obj.service.prototype.display_name

    @staticmethod
    def get_requires(obj):
        if not obj.prototype.requires:
            return None
        comp_list = {}

        def process_requires(req_list):
            for c in req_list:
                _comp = Prototype.obj.get(
                    type="component",
                    name=c["component"],
                    parent__name=c["service"],
                    parent__bundle_id=obj.prototype.bundle_id,
                )
                if _comp == obj.prototype:
                    return
                if _comp.name not in comp_list:
                    comp_list[_comp.name] = {"components": {}, "service": _comp.parent}
                if _comp.name in comp_list[_comp.name]["components"]:
                    return
                comp_list[_comp.name]["components"][_comp.name] = _comp
                if _comp.requires:
                    process_requires(_comp.requires)

        process_requires(obj.requires)
        out = []
        for service_name, params in comp_list.items():
            comp_out = []
            service = params["service"]
            for comp_name in params["components"]:
                comp = params["components"][comp_name]
                comp_out.append(
                    {
                        "prototype_id": comp.id,
                        "name": comp_name,
                        "display_name": comp.display_name,
                    }
                )
            if not comp_out:
                continue
            out.append(
                {
                    "prototype_id": service.id,
                    "name": service_name,
                    "display_name": service.display_name,
                    "components": comp_out,
                }
            )
        return out


class BindSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    export_cluster_id = IntegerField(read_only=True, source="source_cluster_id")
    export_cluster_name = CharField(read_only=True, source="source_cluster")
    export_cluster_prototype_name = SerializerMethodField()
    export_service_id = SerializerMethodField()
    export_service_name = SerializerMethodField()
    import_service_id = SerializerMethodField()
    import_service_name = SerializerMethodField()

    @staticmethod
    def get_export_cluster_prototype_name(obj):
        return obj.source_cluster.prototype.name

    @staticmethod
    def get_export_service_name(obj):
        if obj.source_service:
            return obj.source_service.prototype.name
        return None

    @staticmethod
    def get_export_service_id(obj):
        if obj.source_service:
            return obj.source_service.id
        return None

    @staticmethod
    def get_import_service_id(obj):
        if obj.service:
            return obj.service.id
        return None

    @staticmethod
    def get_import_service_name(obj):
        if obj.service:
            return obj.service.prototype.name
        return None


class ClusterBindSerializer(BindSerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {"bind_id": obj.id, "cluster_id": obj.cluster.id}

    url = MyUrlField(read_only=True, view_name="cluster-bind-details")


class DoBindSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    export_cluster_id = IntegerField()
    export_service_id = IntegerField(required=False, allow_null=True)
    export_cluster_name = CharField(read_only=True)
    export_cluster_prototype_name = CharField(read_only=True)

    def create(self, validated_data):
        export_cluster = check_obj(Cluster, validated_data.get("export_cluster_id"))
        return bind(
            validated_data.get("cluster"),
            None,
            export_cluster,
            validated_data.get("export_service_id", 0),
        )


class PostImportSerializer(EmptySerializer):
    bind = JSONField()

    def create(self, validated_data):
        bind_data = validated_data.get("bind")
        cluster = self.context.get("cluster")
        service = self.context.get("service")
        return multi_bind(cluster, service, bind_data)


class DoClusterUpgradeSerializer(DoUpgradeSerializer):
    hc = JSONField(required=False, default=list)

    def create(self, validated_data):
        upgrade = check_obj(Upgrade, validated_data.get("upgrade_id"), "UPGRADE_NOT_FOUND")
        config = validated_data.get("config", {})
        attr = validated_data.get("attr", {})
        hc = validated_data.get("hc", [])
        return do_upgrade(validated_data.get("obj"), upgrade, config, attr, hc)


class ClusterAuditSerializer(ModelSerializer):
    name = CharField(max_length=80, required=False)
    description = CharField(required=False)

    class Meta:
        model = Cluster
        fields = (
            "name",
            "description",
        )
