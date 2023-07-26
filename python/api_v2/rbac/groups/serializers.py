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

from django.contrib.auth.models import Group as AuthGroup
from rbac.models import Group
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer


class GroupNameSerializer(ModelSerializer):
    display_name = SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "display_name"]

    @staticmethod
    def get_display_name(instance: AuthGroup | Group) -> str:
        if isinstance(instance, AuthGroup):
            return Group.objects.get(group_ptr=instance).display_name

        return instance.display_name
