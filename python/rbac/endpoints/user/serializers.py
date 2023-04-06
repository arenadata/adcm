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

from collections import OrderedDict

from django.contrib.auth.password_validation import validate_password
from rbac.endpoints.fields import PasswordField
from rbac.models import Group, User
from rbac.services.user import create, update
from rbac.validators import (
    ADCMCommonPasswordValidator,
    ADCMLengthPasswordValidator,
    ADCMNumericPasswordValidator,
)
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.fields import (
    BooleanField,
    CharField,
    EmailField,
    IntegerField,
    JSONField,
    RegexField,
)
from rest_framework.relations import HyperlinkedIdentityField
from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer


class UserGroupSerializer(EmptySerializer):
    id = IntegerField()
    url = HyperlinkedIdentityField(view_name="rbac:group-detail")


class GroupUserSerializer(EmptySerializer):
    id = IntegerField()
    url = HyperlinkedIdentityField(view_name="rbac:user-detail")


class ExpandedGroupSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    user = GroupUserSerializer(many=True, source="user_set")
    url = HyperlinkedIdentityField(view_name="rbac:group-detail")
    name = CharField(max_length=150, source="group.display_name")
    type = CharField(read_only=True, source="group.type")

    class Meta:
        model = Group
        fields = ("id", "name", "type", "user", "url")
        expandable_fields = {
            "user": (
                "rbac.endpoints.user.views.UserSerializer",
                {"many": True, "source": "user_set"},
            ),
        }


class UserSerializer(FlexFieldsSerializerMixin, Serializer):
    """
    User serializer
    User model inherits "groups" property from parent class, which refers to "auth.Group",
    so it has not our custom properties in expanded fields
    """

    id = IntegerField(read_only=True)
    username = RegexField(r"^[^\s]+$", max_length=150)
    first_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False, default="")
    last_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False, default="")
    email = EmailField(
        allow_blank=True,
        required=False,
        default="",
    )
    is_superuser = BooleanField(default=False)
    password = PasswordField(trim_whitespace=False)
    current_password = PasswordField(trim_whitespace=False, required=False)
    url = HyperlinkedIdentityField(view_name="rbac:user-detail")
    profile = JSONField(required=False, default="")
    group = UserGroupSerializer(many=True, required=False, source="groups")
    built_in = BooleanField(read_only=True)
    type = CharField(read_only=True)
    is_active = BooleanField(required=False, default=True)

    class Meta:
        expandable_fields = {"group": (ExpandedGroupSerializer, {"many": True, "source": "groups"})}

    def validate(self, attrs: OrderedDict) -> OrderedDict:
        if attrs.get("password"):
            validate_password(
                password=attrs["password"],
                password_validators=[
                    ADCMCommonPasswordValidator(),
                    ADCMNumericPasswordValidator(),
                    ADCMLengthPasswordValidator(),
                ],
            )

        return attrs

    def update(self, instance, validated_data):
        context_user = self.context["request"].user

        return update(
            user=instance,
            context_user=context_user,
            partial=self.partial,
            need_current_password=False,
            **validated_data,
        )

    def create(self, validated_data):
        return create(**validated_data)


class UserAuditSerializer(ModelSerializer):
    group = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "is_superuser",
            "password",
            "profile",
            "group",
        )

    @staticmethod
    def get_group(obj: User) -> list[str, ...]:
        return [group.name for group in obj.groups.all()]
