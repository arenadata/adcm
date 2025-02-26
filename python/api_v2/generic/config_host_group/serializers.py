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

from cm.errors import AdcmEx
from cm.models import ConfigHostGroup, Host
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer

from api_v2.host.serializers import HostShortSerializer


class CHGSerializer(ModelSerializer):
    hosts = HostShortSerializer(many=True, read_only=True)

    class Meta:
        model = ConfigHostGroup
        fields = ["id", "name", "description", "hosts"]

    def validate_name(self, value):
        if isinstance(value, str) and len(value.splitlines()) > 1:
            raise ValidationError("the string field contains a line break character")

        object_ = self.context["view"].get_parent_object()
        parent_content_type = ContentType.objects.get_for_model(model=object_)
        queryset = ConfigHostGroup.objects.filter(name=value, object_type=parent_content_type, object_id=object_.pk)
        if queryset.exists():
            raise AdcmEx(
                code="CREATE_CONFLICT",
                msg=f"Group config with name {value} already exists for {parent_content_type} {object_.name}",
            )
        return value


class HostCHGSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(queryset=Host.objects.all())
    name = CharField()  # for schema without warnings

    class Meta:
        model = Host
        fields = ["id", "name"]
        extra_kwargs = {"name": {"read_only": True}}
