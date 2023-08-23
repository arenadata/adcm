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
from rest_framework.fields import CharField
from rest_framework.serializers import ModelSerializer

from adcm.serializers import EmptySerializer, IdSerializer


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


class GroupNameSerializer(EmptySerializer):
    name = CharField()


class GroupCreateSerializer(EmptySerializer):
    name = CharField()
    description = CharField(allow_blank=True)
    users = IdSerializer(many=True, required=False)

    def validate(self, attrs: dict) -> dict:
        attrs["name_to_display"] = attrs.pop("name")

        if (users := attrs.pop("users", None)) is not None:
            attrs["user_set"] = users

        return attrs


class GroupUpdateSerializer(EmptySerializer):
    display_name = CharField(required=False)
    description = CharField(required=False, allow_blank=True)
    users = IdSerializer(many=True, required=False)

    def validate(self, attrs: dict) -> dict:
        if (display_name := attrs.pop("display_name", None)) is not None:
            attrs["name_to_display"] = display_name

        if (users := attrs.pop("users", None)) is not None:
            attrs["user_set"] = users

        return attrs
