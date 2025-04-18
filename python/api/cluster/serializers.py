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
from cm.api import add_cluster, bind, multi_bind
from cm.errors import AdcmEx
from cm.issue import update_hierarchy_issues
from cm.models import Action, Cluster, Component, Host, HostComponent, Prototype
from cm.schemas import RequiresUISchema
from cm.services.mapping import set_host_component_mapping
from cm.status_api import get_cluster_status, get_hc_status
from cm.upgrade import get_upgrade
from cm.validators import ClusterUniqueValidator, StartMidEndValidator
from core.cluster.types import HostComponentEntry
from django.conf import settings
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (
    BooleanField,
    CharField,
    HyperlinkedIdentityField,
    HyperlinkedRelatedField,
    IntegerField,
    JSONField,
    ModelSerializer,
    Serializer,
    SerializerMethodField,
)

from api.action.serializers import ActionShort
from api.component.serializers import ComponentShortSerializer
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.config_host_group.serializers import CHGsHyperlinkedIdentityField
from api.host.serializers import HostSerializer
from api.serializers import DoUpgradeSerializer, StringListSerializer
from api.utils import CommonAPIURL, ObjectURL, UrlField, check_obj, filter_actions, get_requires


def get_cluster_id(obj):
    if hasattr(obj.obj_ref, "service"):
        return obj.obj_ref.service.cluster.id
    else:
        return obj.obj_ref.cluster.id


class ClusterSerializer(Serializer):
    id = IntegerField(read_only=True)
    prototype_id = IntegerField(help_text="ID of Cluster type")
    name = CharField(
        help_text="Cluster name",
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
    description = CharField(help_text="Cluster description", required=False)
    state = CharField(read_only=True)
    before_upgrade = JSONField(read_only=True)
    url = HyperlinkedIdentityField(view_name="v1:cluster-details", lookup_field="id", lookup_url_kwarg="cluster_id")

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
    action = CommonAPIURL(view_name="v1:object-action")
    service = ObjectURL(view_name="v1:service")
    host = ObjectURL(view_name="v1:host")
    hostcomponent = HyperlinkedIdentityField(
        view_name="v1:host-component",
        lookup_field="id",
        lookup_url_kwarg="cluster_id",
    )
    status = SerializerMethodField()
    status_url = HyperlinkedIdentityField(
        view_name="v1:cluster-status", lookup_field="id", lookup_url_kwarg="cluster_id"
    )
    config = CommonAPIURL(view_name="v1:object-config")
    serviceprototype = HyperlinkedIdentityField(
        view_name="v1:cluster-service-prototype",
        lookup_field="id",
        lookup_url_kwarg="cluster_id",
    )
    upgrade = HyperlinkedIdentityField(view_name="v1:cluster-upgrade", lookup_field="id", lookup_url_kwarg="cluster_id")
    imports = HyperlinkedIdentityField(view_name="v1:cluster-import", lookup_field="id", lookup_url_kwarg="cluster_id")
    bind = HyperlinkedIdentityField(view_name="v1:cluster-bind", lookup_field="id", lookup_url_kwarg="cluster_id")
    prototype = HyperlinkedRelatedField(
        view_name="v1:cluster-prototype-detail",
        read_only=True,
        lookup_url_kwarg="prototype_pk",
    )
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    group_config = CHGsHyperlinkedIdentityField(view_name="v1:group-config-list")

    @staticmethod
    def get_status(obj: Cluster) -> int:
        return get_cluster_status(obj)


class ClusterUISerializer(ClusterDetailSerializer):
    action = CommonAPIURL(view_name="v1:object-action")
    edition = CharField(read_only=True)
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    upgrade = HyperlinkedIdentityField(view_name="v1:cluster-upgrade", lookup_field="id", lookup_url_kwarg="cluster_id")
    upgradable = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    status = SerializerMethodField()

    @staticmethod
    def get_upgradable(obj: Cluster) -> bool:
        return bool(get_upgrade(obj))

    @staticmethod
    def get_prototype_version(obj: Cluster) -> str:
        return obj.prototype.version

    @staticmethod
    def get_prototype_name(obj: Cluster) -> str:
        return obj.prototype.name

    @staticmethod
    def get_prototype_display_name(obj: Cluster) -> str | None:
        return obj.prototype.display_name

    @staticmethod
    def get_status(obj: Cluster) -> int:
        return get_cluster_status(obj)


class ClusterUpdateSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(
        max_length=80,
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
    description = CharField(required=False, help_text="Cluster description")

    def update(self, instance, validated_data):
        if validated_data.get("name") and validated_data.get("name") != instance.name and instance.state != "created":
            raise ValidationError("Name change is available only in the 'created' state")

        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.save()
        update_hierarchy_issues(instance)

        return instance


class ClusterDetailUISerializer(ClusterDetailSerializer):
    actions = SerializerMethodField()
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    upgradable = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context["object"] = obj
        self.context["cluster_id"] = obj.id
        actions = ActionShort(filter_actions(obj, act_set), many=True, context=self.context)

        return actions.data

    @staticmethod
    def get_upgradable(obj: Cluster) -> bool:
        return bool(get_upgrade(obj))

    @staticmethod
    def get_prototype_version(obj: Cluster) -> str:
        return obj.prototype.version

    @staticmethod
    def get_prototype_name(obj: Cluster) -> str:
        return obj.prototype.name

    @staticmethod
    def get_prototype_display_name(obj: Cluster) -> str | None:
        return obj.prototype.display_name

    @staticmethod
    def get_main_info(obj: Cluster) -> str | None:
        return get_main_info(obj)


class ClusterStatusSerializer(EmptySerializer):
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
    host_url = HyperlinkedIdentityField(view_name="host-details", lookup_field="host_id", lookup_url_kwarg="host_id")

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

    def get_host(self, obj):  # noqa: ARG001, ARG002
        hosts = Host.objects.filter(cluster=self.context.get("cluster"))

        return HostSerializer(hosts, many=True, context=self.context).data

    def get_component(self, obj):  # noqa: ARG001, ARG002
        comps = Component.objects.filter(cluster=self.context.get("cluster"))

        return HCComponentSerializer(comps, many=True, context=self.context).data


class HostComponentSaveSerializer(EmptySerializer):
    hc = JSONField()

    @staticmethod
    def validate_hc(hostcomponent):
        if not hostcomponent:
            raise AdcmEx("INVALID_INPUT", "hc field is required")

        if not isinstance(hostcomponent, list):
            raise AdcmEx("INVALID_INPUT", "hc field should be a list")

        added = set()

        for item in hostcomponent:
            for key in ("component_id", "host_id", "service_id"):
                if key not in item:
                    msg = '"{}" sub-field is required'

                    raise AdcmEx("INVALID_INPUT", msg.format(key))

            entry = tuple(item.values())
            if entry in added:
                raise AdcmEx(
                    "INVALID_INPUT",
                    msg=f"duplicated entry: {item}",
                )

            added.add(entry)

        return hostcomponent

    def create(self, validated_data):
        hostcomponent = validated_data.get("hc")
        new_mapping_entries = {
            HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"]) for entry in hostcomponent
        }

        cluster = self.context.get("cluster")

        set_host_component_mapping(
            cluster_id=cluster.id, bundle_id=cluster.prototype.bundle_id, new_mapping=new_mapping_entries
        )

        return HostComponent.objects.filter(cluster_id=cluster.id)


class HCComponentSerializer(ComponentShortSerializer):
    service_id = IntegerField(read_only=True)
    service_name = SerializerMethodField()
    service_display_name = SerializerMethodField()
    service_state = SerializerMethodField()
    requires = SerializerMethodField()

    @staticmethod
    def get_service_state(obj: Component) -> str:
        return obj.service.state

    @staticmethod
    def get_service_name(obj: Component) -> str:
        return obj.service.prototype.name

    @staticmethod
    def get_service_display_name(obj: Component) -> str:
        return obj.service.prototype.display_name

    @staticmethod
    def get_requires(obj: Component) -> list[RequiresUISchema] | None:
        return get_requires(prototype=obj.prototype)


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


class ClusterAuditSerializer(ModelSerializer):
    name = CharField(max_length=80, required=False)
    description = CharField(required=False)

    class Meta:
        model = Cluster
        fields = (
            "name",
            "description",
        )
