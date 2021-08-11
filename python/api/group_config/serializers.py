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
from rest_framework import serializers
from rest_framework.reverse import reverse

from cm.models import GroupConfig


class ObjectTypeField(serializers.Field):
    def to_representation(self, value):
        if value.model == 'clusterobject':
            return 'service'
        elif value.model == 'servicecomponent':
            return 'component'
        elif value.model == 'hostprovider':
            return 'provider'
        else:
            return value.model

    def to_internal_value(self, data):
        if data == 'service':
            data = 'clusterobject'
        elif data == 'component':
            data = 'servicecomponent'
        elif data == 'provider':
            data = 'hostprovider'
        return ContentType.objects.get(app_label='cm', model=data)


class GroupConfigSerializer(serializers.ModelSerializer):
    object_type = ObjectTypeField()
    url = serializers.HyperlinkedIdentityField(view_name='group-config-detail')
    hosts = serializers.SerializerMethodField()
    config = serializers.HyperlinkedRelatedField(view_name='config-detail', read_only=True)

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
            'url',
        )

    def get_hosts(self, obj):
        url = reverse(
            viewname='host',
            request=self.context['request'],
            format=self.context['format'],
        )
        return f'{url}?groupconfig={obj.id}'
