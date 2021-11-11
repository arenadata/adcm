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
from rest_framework.reverse import reverse
from rest_framework_extensions.settings import extensions_api_settings

from api.api_views import check_obj, hlink, UrlField
from cm.adcm_config import ui_config
from cm.errors import raise_AdcmEx
from cm.models import Upgrade, GroupConfig
from cm.upgrade import do_upgrade


class EmptySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)


class UpgradeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(required=False)
    bundle_id = serializers.IntegerField(read_only=True)
    description = serializers.CharField(required=False)
    min_version = serializers.CharField(required=False)
    max_version = serializers.CharField(required=False)
    min_strict = serializers.BooleanField(required=False)
    max_strict = serializers.BooleanField(required=False)
    upgradable = serializers.BooleanField(required=False)
    license = serializers.CharField(required=False)
    license_url = hlink('bundle-license', 'bundle_id', 'bundle_id')
    from_edition = serializers.JSONField(required=False)
    state_available = serializers.JSONField(required=False)
    state_on_success = serializers.CharField(required=False)


class UpgradeLinkSerializer(UpgradeSerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {'cluster_id': self.context['cluster_id'], 'upgrade_id': obj.id}

    url = MyUrlField(read_only=True, view_name='cluster-upgrade-details')
    do = MyUrlField(read_only=True, view_name='do-cluster-upgrade')


class DoUpgradeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    upgradable = serializers.BooleanField(read_only=True)

    def create(self, validated_data):
        upgrade = check_obj(Upgrade, validated_data.get('upgrade_id'), 'UPGRADE_NOT_FOUND')
        return do_upgrade(validated_data.get('obj'), upgrade)


class StringListSerializer(serializers.ListField):
    item = serializers.CharField()


class UIConfigField(serializers.JSONField):
    """Serializering config field for UI"""

    def to_representation(self, value):
        obj = value.obj_ref.object
        if obj is None:
            raise_AdcmEx('INVALID_CONFIG_UPDATE', f'unknown object type "{value.obj_ref}"')
        if isinstance(obj, GroupConfig):
            obj = obj.object
        return ui_config(obj, value)

    def to_internal_value(self, data):
        return {'config': data}


class MultiHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    """
    Hyperlinked identity field for nested routers
    """

    def __init__(self, view_name, *args, **kwargs):
        self.url_args = args
        super().__init__(view_name=view_name, **kwargs)

    def get_url(self, obj, view_name, request, format):  # pylint: disable=redefined-builtin
        kwargs = {}
        for url_arg in self.url_args:
            if url_arg.startswith(extensions_api_settings.DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX):
                parent_name = url_arg.replace(
                    extensions_api_settings.DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX, '', 1
                )
                parent = self.context.get(parent_name)
                kwargs.update({url_arg: parent.id})
            else:
                kwargs.update({url_arg: obj.id})
        return reverse(viewname=view_name, kwargs=kwargs, request=request, format=format)


class MultiHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):
    """
    Hyperlinked related field for nested routers
    """

    def __init__(self, view_name, *args, **kwargs):
        kwargs['read_only'] = True
        self.url_args = args
        super().__init__(view_name, **kwargs)

    def get_url(self, obj, view_name, request, format):  # pylint: disable=redefined-builtin
        kwargs = {}
        for url_arg in self.url_args:
            if url_arg.startswith(extensions_api_settings.DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX):
                parent_name = url_arg.replace(
                    extensions_api_settings.DEFAULT_PARENT_LOOKUP_KWARG_NAME_PREFIX, '', 1
                )
                parent = self.context.get(parent_name)
                if parent is None:
                    parent = obj
                kwargs.update({url_arg: parent.id})
        lookup_value = getattr(obj, self.lookup_field)
        if lookup_value is None:
            return lookup_value
        kwargs.update({self.lookup_url_kwarg: lookup_value})
        return reverse(viewname=view_name, kwargs=kwargs, request=request, format=format)
