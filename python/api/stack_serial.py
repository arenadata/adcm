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

from rest_framework import serializers

from cm.logger import log   # pylint: disable=unused-import
import cm.config as config
from cm.models import ClusterObject, Prototype, Bundle
from api.serializers import hlink, UrlField
from api.serializers import ActionDetailSerializer, ConfigSerializer, UpgradeSerializer


class Stack(serializers.Serializer):
    load = UrlField(view_name='load-bundle')
    upload = UrlField(view_name='upload-bundle')
    bundle = UrlField(view_name='bundle')
    prototype = UrlField(view_name='prototype')
    service = UrlField(view_name='service-type')
    host = UrlField(view_name='host-type')
    provider = UrlField(view_name='provider-type')
    cluster = UrlField(view_name='cluster-type')


class LoadBundle(serializers.Serializer):
    bundle_file = serializers.CharField()


class UploadBundle(serializers.Serializer):
    file = serializers.FileField(help_text='bundle file for upload')

    def create(self, validated_data):
        fd = self.context['request'].data['file']
        fname = '{}/{}'.format(config.DOWNLOAD_DIR, fd)
        with open(fname, 'wb+') as dest:
            for chunk in fd.chunks():
                dest.write(chunk)
        return Bundle()


class BundleSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    edition = serializers.CharField(read_only=True)
    hash = serializers.CharField(read_only=True)
    license = serializers.CharField(read_only=True)
    license_path = serializers.CharField(read_only=True)
    license_hash = serializers.CharField(read_only=True)
    description = serializers.CharField(required=False)
    date = serializers.DateTimeField(read_only=True)
    url = hlink('bundle-details', 'id', 'bundle_id')
    license_url = hlink('bundle-license', 'id', 'bundle_id')
    update = hlink('bundle-update', 'id', 'bundle_id')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        proto = Prototype.objects.filter(bundle=instance, name=instance.name)
        data['adcm_min_version'] = proto[0].adcm_min_version
        data['display_name'] = proto[0].display_name
        return data


class LicenseSerializer(serializers.Serializer):
    license = serializers.CharField(read_only=True)
    text = serializers.CharField(read_only=True)
    accept = hlink('accept-license', 'id', 'bundle_id')


class PrototypeSerializer(serializers.Serializer):
    bundle_id = serializers.IntegerField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    path = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(required=False)
    version = serializers.CharField(read_only=True)
    bundle_edition = serializers.SerializerMethodField()
    description = serializers.CharField(required=False)
    type = serializers.CharField(read_only=True)
    required = serializers.BooleanField(read_only=True)
    url = hlink('prototype-details', 'id', 'prototype_id')

    def get_bundle_edition(self, obj):
        return obj.bundle.edition


class PrototypeShort(serializers.ModelSerializer):
    class Meta:
        model = Prototype
        fields = ('name',)


class ComponentSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    display_name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    params = serializers.JSONField(required=False)
    constraint = serializers.JSONField(required=False)
    requires = serializers.JSONField(required=False)
    monitoring = serializers.CharField(read_only=True)


class ExportSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)


class ImportSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    min_version = serializers.CharField(read_only=True)
    max_version = serializers.CharField(read_only=True)
    min_strict = serializers.BooleanField(required=False)
    max_strict = serializers.BooleanField(required=False)
    default = serializers.JSONField(read_only=True)
    required = serializers.BooleanField(read_only=True)
    multibind = serializers.BooleanField(read_only=True)


class ServiceSerializer(PrototypeSerializer):
    shared = serializers.BooleanField(read_only=True)
    monitoring = serializers.CharField(read_only=True)
    url = hlink('service-type-details', 'id', 'prototype_id')


class ServiceDetailSerializer(ServiceSerializer):
    actions = ActionDetailSerializer(many=True, read_only=True)
    components = ComponentSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    exports = ExportSerializer(many=True, read_only=True)
    imports = ImportSerializer(many=True, read_only=True)


class BundleServiceUISerializer(ServiceSerializer):
    selected = serializers.SerializerMethodField()

    def get_selected(self, obj):
        cluster = self.context.get('cluster')
        try:
            ClusterObject.objects.get(cluster=cluster, prototype=obj)
            return True
        except ClusterObject.DoesNotExist:
            return False


class AdcmTypeSerializer(PrototypeSerializer):
    url = hlink('adcm-type-details', 'id', 'prototype_id')


class ClusterTypeSerializer(PrototypeSerializer):
    license = serializers.SerializerMethodField()
    url = hlink('cluster-type-details', 'id', 'prototype_id')

    def get_license(self, obj):
        return obj.bundle.license


class HostTypeSerializer(PrototypeSerializer):
    monitoring = serializers.CharField(read_only=True)
    url = hlink('host-type-details', 'id', 'prototype_id')


class ProviderTypeSerializer(PrototypeSerializer):
    license = serializers.SerializerMethodField()
    url = hlink('provider-type-details', 'id', 'prototype_id')

    def get_license(self, obj):
        return obj.bundle.license


class PrototypeDetailSerializer(PrototypeSerializer):
    actions = ActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)


class ProviderTypeDetailSerializer(ProviderTypeSerializer):
    actions = ActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    upgrade = UpgradeSerializer(many=True, read_only=True)


class HostTypeDetailSerializer(HostTypeSerializer):
    actions = ActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)


class AdcmTypeDetailSerializer(AdcmTypeSerializer):
    actions = ActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)


class ClusterTypeDetailSerializer(ClusterTypeSerializer):
    actions = ActionDetailSerializer(many=True, read_only=True)
    config = ConfigSerializer(many=True, read_only=True)
    upgrade = UpgradeSerializer(many=True, read_only=True)
    exports = ExportSerializer(many=True, read_only=True)
    imports = ImportSerializer(many=True, read_only=True)
