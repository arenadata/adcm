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

from django.contrib.contenttypes.models import ContentType
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework_extensions.settings import extensions_api_settings

from cm.errors import AdcmEx
from cm.models import GroupConfig, Host


class HostFlexFieldsSerializer(FlexFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Host
        fields = (
            'id',
            'cluster_id',
            'prototype_id',
            'provider_id',
            'fqdn',
            'state',
        )


def check_object_type(type_name):
    """Object type checking"""
    if type_name not in ['cluster', 'service', 'component', 'provider']:
        raise AdcmEx('GROUP_CONFIG_TYPE_ERROR')


def translate_model_name(model_name):
    """Translating model name to display model name"""
    if model_name == 'clusterobject':
        return 'service'
    elif model_name == 'servicecomponent':
        return 'component'
    elif model_name == 'hostprovider':
        return 'provider'
    else:
        return model_name


def revert_model_name(name):
    """Translating display model name to model name"""
    if name == 'service':
        return 'clusterobject'
    elif name == 'component':
        return 'servicecomponent'
    elif name == 'provider':
        return 'hostprovider'
    else:
        return name


class ObjectTypeField(serializers.Field):
    def to_representation(self, value):
        return translate_model_name(value.model)

    def to_internal_value(self, data):
        check_object_type(data)
        return ContentType.objects.get(app_label='cm', model=revert_model_name(data))


class GroupConfigsHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    """Return url for group_configs for Cluster, Provider, Component or Service"""

    def get_url(self, obj, view_name, request, format):  # pylint: disable=redefined-builtin
        url = reverse(viewname=view_name, request=request, format=format)
        return f'{url}?object_id={obj.id}&object_type={obj.prototype.type}'


class GroupConfigSerializer(FlexFieldsSerializerMixin, serializers.ModelSerializer):
    object_type = ObjectTypeField()
    url = serializers.HyperlinkedIdentityField(view_name='group-config-detail')
    hosts = serializers.HyperlinkedRelatedField(
        view_name='group-config-host-list',
        read_only=True,
        lookup_url_kwarg='parent_lookup_groupconfig',
        source='*',
    )
    config = serializers.HyperlinkedRelatedField(view_name='config-detail', read_only=True)
    host_candidate = serializers.HyperlinkedRelatedField(
        view_name='group-config-host-candidate-list',
        read_only=True,
        lookup_url_kwarg='parent_lookup_groupconfig',
        source='*',
    )

    class Meta:
        model = GroupConfig
        fields = (
            'id',
            'object_id',
            'object_type',
            'name',
            'description',
            'hosts',
            'config',
            'host_candidate',
            'url',
        )
        expandable_fields = {
            'hosts': (HostFlexFieldsSerializer, {'many': True}),
            'host_candidate': (HostFlexFieldsSerializer, {'many': True}),
        }


class MultiHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    """
    A read-only field that represents the identity URL for an object, itself.
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


class GroupConfigHostSerializer(serializers.ModelSerializer):
    """Serializer for hosts in group config"""

    id = serializers.PrimaryKeyRelatedField(queryset=Host.objects.all())
    url = MultiHyperlinkedIdentityField(
        'group-config-host-detail', 'parent_lookup_groupconfig', 'pk'
    )

    class Meta:
        model = Host
        fields = (
            'id',
            'cluster_id',
            'prototype_id',
            'provider_id',
            'fqdn',
            'description',
            'state',
            'url',
        )
        read_only_fields = (
            'state',
            'fqdn',
            'description',
            'prototype_id',
            'provider_id',
            'cluster_id',
        )

    def create(self, validated_data):
        group_config = self.context.get('groupconfig')
        host = validated_data['id']
        group_config.hosts.add(host)
        return host


class GroupConfigHostCandidateSerializer(GroupConfigHostSerializer):
    """Serializer for host candidate"""

    url = serializers.HyperlinkedIdentityField('host-details', lookup_url_kwarg='host_id')
