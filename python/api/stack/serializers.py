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

from api.action.serializers import StackActionDetailSerializer
from api.config.serializers import ConfigSerializer
from api.serializers import UpgradeSerializer
from api.utils import get_requires
from cm.models import Bundle, ClusterObject, Prototype
from cm.schemas import RequiresUISchema
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.serializers import (
    BooleanField,
    CharField,
    FileField,
    HyperlinkedIdentityField,
    HyperlinkedModelSerializer,
    IntegerField,
    JSONField,
    ModelSerializer,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer


class UploadBundleSerializer(EmptySerializer):
    file = FileField(help_text="bundle file for upload")


class LoadBundleSerializer(EmptySerializer):
    bundle_file = CharField()


class BundleSerializer(HyperlinkedModelSerializer):
    license_url = HyperlinkedIdentityField(view_name="bundle-license", lookup_field="pk", lookup_url_kwarg="bundle_pk")
    update = HyperlinkedIdentityField(view_name="bundle-update", lookup_field="pk", lookup_url_kwarg="bundle_pk")
    license = SerializerMethodField()

    class Meta:
        model = Bundle
        fields = (
            "id",
            "name",
            "version",
            "edition",
            "license",
            "hash",
            "description",
            "date",
            "license_url",
            "update",
            "url",
        )
        read_only_fields = fields
        extra_kwargs = {"url": {"lookup_url_kwarg": "bundle_pk"}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        proto = Prototype.objects.filter(bundle=instance, name=instance.name).first()
        data["adcm_min_version"] = proto.adcm_min_version
        data["display_name"] = proto.display_name

        return data

    def get_license(self, obj: Bundle) -> str | None:
        proto = Prototype.objects.filter(bundle=obj, name=obj.name).first()
        if proto:
            return proto.license

        return None


class PrototypeSerializer(HyperlinkedModelSerializer):
    license_url = HyperlinkedIdentityField(
        view_name="prototype-license",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )
    bundle_edition = CharField(source="bundle.edition")

    class Meta:
        model = Prototype
        fields = (
            "id",
            "bundle_id",
            "type",
            "path",
            "name",
            "license",
            "license_path",
            "license_hash",
            "license_url",
            "display_name",
            "version",
            "required",
            "requires",
            "description",
            "bundle_edition",
            "url",
        )
        read_only_fields = fields
        extra_kwargs = {"url": {"lookup_url_kwarg": "prototype_pk"}}


class PrototypeSerializerMixin:
    @staticmethod
    def get_constraint(obj: Prototype) -> list[dict]:
        if obj.type == "component":
            return obj.constraint

        return []

    @staticmethod
    def get_service_name(obj):
        if obj.type == "component":
            return obj.parent.name

        return ""

    @staticmethod
    def get_service_display_name(obj):
        if obj.type == "component":
            return obj.parent.display_name

        return ""

    @staticmethod
    def get_service_id(obj):
        if obj.type == "component":
            return obj.parent.id

        return None


class PrototypeUISerializer(PrototypeSerializer, PrototypeSerializerMixin):
    constraint = SerializerMethodField(read_only=True)
    service_name = SerializerMethodField(read_only=True)
    service_display_name = SerializerMethodField(read_only=True)
    service_id = SerializerMethodField(read_only=True)
    requires = SerializerMethodField(read_only=True)

    class Meta:
        model = Prototype
        fields = (
            *PrototypeSerializer.Meta.fields,
            "parent_id",
            "version_order",
            "shared",
            "constraint",
            "requires",
            "bound_to",
            "adcm_min_version",
            "monitoring",
            "config_group_customization",
            "venv",
            "allow_maintenance_mode",
            "service_name",
            "service_display_name",
            "service_id",
        )
        read_only_fields = fields
        extra_kwargs = {"url": {"lookup_url_kwarg": "prototype_pk"}}

    @staticmethod
    def get_requires(obj: Prototype) -> list[RequiresUISchema] | None:
        return get_requires(prototype=obj)


class PrototypeDetailSerializer(PrototypeSerializer, PrototypeSerializerMixin):
    constraint = SerializerMethodField()
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    service_name = SerializerMethodField(read_only=True)
    service_display_name = SerializerMethodField(read_only=True)
    service_id = SerializerMethodField(read_only=True)

    class Meta:
        model = Prototype
        fields = (
            *PrototypeSerializer.Meta.fields,
            "constraint",
            "requires",
            "actions",
            "config",
            "service_name",
            "service_display_name",
            "service_id",
        )
        read_only_fields = fields
        extra_kwargs = {"url": {"lookup_url_kwarg": "prototype_pk"}}


class PrototypeShort(ModelSerializer):
    class Meta:
        model = Prototype
        fields = ("name",)


class ExportSerializer(EmptySerializer):
    name = CharField(read_only=True)


class ImportSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(read_only=True)
    min_version = CharField(read_only=True)
    max_version = CharField(read_only=True)
    min_strict = BooleanField(required=False)
    max_strict = BooleanField(required=False)
    default = JSONField(read_only=True)
    required = BooleanField(read_only=True)
    multibind = BooleanField(read_only=True)


class ComponentPrototypeSerializer(PrototypeSerializer):
    url = HyperlinkedIdentityField(
        view_name="component-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )

    class Meta:
        model = Prototype
        fields = (
            *PrototypeSerializer.Meta.fields,
            "constraint",
            "requires",
            "bound_to",
            "monitoring",
            "url",
        )
        read_only_fields = fields


class ComponentPrototypeUISerializer(ComponentPrototypeSerializer):
    requires = SerializerMethodField()

    @staticmethod
    def get_requires(obj: Prototype) -> list[RequiresUISchema] | None:
        return get_requires(prototype=obj)


class ServicePrototypeSerializer(PrototypeSerializer):
    url = HyperlinkedIdentityField(
        view_name="service-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )

    class Meta:
        model = Prototype
        fields = (
            *PrototypeSerializer.Meta.fields,
            "shared",
            "monitoring",
            "url",
        )
        read_only_fields = fields


class ServiceDetailPrototypeSerializer(ServicePrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    components = ComponentPrototypeSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    exports = ExportSerializer(many=True, read_only=True)
    imports = ImportSerializer(many=True, read_only=True)

    class Meta:
        model = Prototype
        fields = (
            *ServicePrototypeSerializer.Meta.fields,
            "actions",
            "components",
            "config",
            "exports",
            "imports",
        )
        read_only_fields = fields


class BundleServiceUIPrototypeSerializer(ServicePrototypeSerializer):
    selected = SerializerMethodField()
    requires = SerializerMethodField(read_only=True)

    class Meta:
        model = Prototype
        fields = (
            *ServicePrototypeSerializer.Meta.fields,
            "selected",
        )
        read_only_fields = fields

    def get_selected(self, obj):
        cluster = self.context.get("cluster")
        try:
            ClusterObject.objects.get(cluster=cluster, prototype=obj)

            return True
        except ClusterObject.DoesNotExist:
            return False

    @staticmethod
    def get_requires(obj: Prototype) -> list[RequiresUISchema] | None:
        return get_requires(prototype=obj)


class ADCMPrototypeSerializer(PrototypeSerializer):
    url = HyperlinkedIdentityField(
        view_name="adcm-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )

    class Meta:
        model = Prototype
        fields = (
            *PrototypeSerializer.Meta.fields,
            "url",
        )
        read_only_fields = fields


class ClusterPrototypeSerializer(FlexFieldsSerializerMixin, PrototypeSerializer):
    url = HyperlinkedIdentityField(
        view_name="cluster-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )

    class Meta:
        model = Prototype
        fields = (
            *PrototypeSerializer.Meta.fields,
            "url",
        )
        read_only_fields = fields


class HostPrototypeSerializer(PrototypeSerializer):
    monitoring = CharField(read_only=True)
    url = HyperlinkedIdentityField(
        view_name="host-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )

    class Meta:
        model = Prototype
        fields = (
            *PrototypeSerializer.Meta.fields,
            "monitoring",
            "url",
        )
        read_only_fields = fields


class ProviderPrototypeSerializer(FlexFieldsSerializerMixin, PrototypeSerializer):
    url = HyperlinkedIdentityField(
        view_name="provider-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )

    class Meta:
        model = Prototype
        fields = (
            *PrototypeSerializer.Meta.fields,
            "url",
        )
        read_only_fields = fields


class ProviderPrototypeDetailSerializer(ProviderPrototypeSerializer):  # pylint: disable=too-many-ancestors
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    upgrade = UpgradeSerializer(many=True, read_only=True)

    class Meta:
        model = Prototype
        fields = (
            *ProviderPrototypeSerializer.Meta.fields,
            "actions",
            "config",
            "upgrade",
        )
        read_only_fields = fields


class HostPrototypeDetailSerializer(HostPrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)

    class Meta:
        model = Prototype
        fields = (
            *HostPrototypeSerializer.Meta.fields,
            "actions",
            "config",
        )
        read_only_fields = fields


class ComponentPrototypeDetailSerializer(ComponentPrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)

    class Meta:
        model = Prototype
        fields = (
            *ComponentPrototypeSerializer.Meta.fields,
            "actions",
            "config",
        )
        read_only_fields = fields


class ADCMPrototypeDetailSerializer(ADCMPrototypeSerializer):
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)

    class Meta:
        model = Prototype
        fields = (
            *ADCMPrototypeSerializer.Meta.fields,
            "actions",
            "config",
        )
        read_only_fields = fields


class ClusterPrototypeDetailSerializer(ClusterPrototypeSerializer):  # pylint: disable=too-many-ancestors
    actions = StackActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    upgrade = UpgradeSerializer(many=True, read_only=True)
    exports = ExportSerializer(many=True, read_only=True)
    imports = ImportSerializer(many=True, read_only=True)

    class Meta:
        model = Prototype
        fields = (
            *ADCMPrototypeSerializer.Meta.fields,
            "actions",
            "config",
            "upgrade",
            "exports",
            "imports",
        )
        read_only_fields = fields
