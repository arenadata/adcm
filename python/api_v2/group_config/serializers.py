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
from cm.models import GroupConfig
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer

from api_v2.host.serializers import HostShortSerializer


class GroupConfigSerializer(ModelSerializer):
    hosts = HostShortSerializer(many=True, read_only=True)

    class Meta:
        model = GroupConfig
        fields = ["id", "name", "description", "hosts"]

    def validate_name(self, value):
        model = self.context["view"].get_parent_object()
        parent_content_type = ContentType.objects.get_for_model(model=model)
        queryset = GroupConfig.objects.filter(name=value, object_type=parent_content_type)
        if queryset.exists():
            raise ValidationError(
                f"Group config with name {value} already exists for {parent_content_type} {model.name}"
            )
        return value
