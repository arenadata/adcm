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
from rbac.services import group as group_services
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.fields import BooleanField, CharField, IntegerField, RegexField
from rest_framework.relations import HyperlinkedIdentityField
from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer


class GroupUserSerializer(EmptySerializer):
    id = IntegerField()
    url = HyperlinkedIdentityField(view_name="v1:rbac:user-detail")


class UserGroupSerializer(EmptySerializer):
    id = IntegerField()
    url = HyperlinkedIdentityField(view_name="v1:rbac:group-detail")


class ExpandedUserSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    group = UserGroupSerializer(many=True, source="groups")
    url = HyperlinkedIdentityField(view_name="v1:rbac:user-detail")

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_superuser",
            "group",
            "url",
        )
        expandable_fields = {
            "group": (
                "rbac.endpoints.group.views.GroupSerializer",
                {"many": True, "source": "groups"},
            ),
        }


class GroupSerializer(FlexFieldsSerializerMixin, Serializer):
    """
    Group serializer
    Group model inherits "user_set" property from parent class, which refers to "auth.User",
    so it has not our custom properties in expanded fields
    """

    id = IntegerField(read_only=True)
    name = RegexField(r"^[^\n]+$", max_length=100, source="name_to_display")
    description = CharField(max_length=255, allow_blank=True, required=False, default="")
    user = GroupUserSerializer(many=True, required=False, source="user_set")
    url = HyperlinkedIdentityField(view_name="v1:rbac:group-detail")
    built_in = BooleanField(read_only=True)
    type = CharField(read_only=True)

    class Meta:
        expandable_fields = {"user": (ExpandedUserSerializer, {"many": True, "source": "user_set"})}

    def update(self, instance, validated_data):
        return group_services.update(instance, partial=self.partial, **validated_data)

    def create(self, validated_data):
        return group_services.create(**validated_data)


class GroupAuditSerializer(ModelSerializer):
    name = CharField(source="name_to_display")
    user = SerializerMethodField()

    class Meta:
        model = Group
        fields = ("name", "description", "user")

    @staticmethod
    def get_user(obj: Group) -> list[str, ...]:
        return [user.username for user in obj.user_set.all()]
