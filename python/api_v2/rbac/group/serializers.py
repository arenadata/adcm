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

from rbac.models import Group, User
from rest_framework.serializers import (
    CharField,
    ManyRelatedField,
    ModelSerializer,
    PrimaryKeyRelatedField,
)

from adcm.serializers import EmptySerializer


class RelatedUserSerializer(ModelSerializer):
    username = CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username"]


class GroupSerializer(ModelSerializer):
    users = RelatedUserSerializer(source="user_set", many=True)

    class Meta:
        model = Group
        fields = ["id", "name", "display_name", "description", "users", "type"]


class GroupRelatedSerializer(EmptySerializer):
    name = CharField()


class GroupCreateUpdateSerializer(ModelSerializer):
    users = ManyRelatedField(
        child_relation=PrimaryKeyRelatedField(queryset=User.objects.all()), source="user_set", required=False
    )

    class Meta:
        model = Group
        fields = ("display_name", "description", "users")
        extra_kwargs = {
            "display_name": {"required": True},
            "description": {"default": "", "allow_blank": True, "required": False},
        }
