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

from adcm.serializers import EmptySerializer
from cm.errors import AdcmEx
from django.conf import settings
from rbac.models import Group, User
from rbac.utils import Empty
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
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_409_CONFLICT

from api.rbac.utils import create_user, update_user


class UserGroupSerializer(EmptySerializer):
    id = IntegerField()
    url = HyperlinkedIdentityField(view_name="v1:rbac:group-detail")


class GroupUserSerializer(EmptySerializer):
    id = IntegerField()
    url = HyperlinkedIdentityField(view_name="v1:rbac:user-detail")


class ExpandedGroupSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    user = GroupUserSerializer(many=True, source="user_set")
    url = HyperlinkedIdentityField(view_name="v1:rbac:group-detail")
    name = CharField(max_length=150, source="group.display_name")
    type = CharField(read_only=True, source="group.type")

    class Meta:
        model = Group
        fields = ("id", "name", "type", "user", "url")
        expandable_fields = {
            "user": (
                "rbac.user.views.UserSerializer",
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
    username = RegexField(r"^[^\s]+$", max_length=settings.USERNAME_MAX_LENGTH)
    first_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False, default="")
    last_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False, default="")
    email = EmailField(
        allow_blank=True,
        required=False,
        default="",
    )
    is_superuser = BooleanField(default=False)
    password = CharField(trim_whitespace=False, write_only=True, required=False)
    current_password = CharField(trim_whitespace=False, required=False)
    url = HyperlinkedIdentityField(view_name="v1:rbac:user-detail")
    profile = JSONField(required=False, default="")
    group = UserGroupSerializer(many=True, required=False, source="groups")
    built_in = BooleanField(read_only=True)
    type = CharField(read_only=True)
    is_active = BooleanField(required=False, default=True)
    failed_login_attempts = IntegerField(read_only=True)

    class Meta:
        expandable_fields = {"group": (ExpandedGroupSerializer, {"many": True, "source": "groups"})}

    def update(self, instance, validated_data):
        context_user = self.context["request"].user

        if context_user.is_superuser and context_user.pk == instance.pk and validated_data.get("is_superuser") is False:
            raise AdcmEx(
                code="USER_UPDATE_ERROR",
                http_code=HTTP_409_CONFLICT,
                msg="You can't withdraw ADCM Administrator's rights from yourself.",
            )

        new_password = validated_data.get("password", Empty)
        if not context_user.is_superuser:
            if new_password is not Empty:
                raise AdcmEx(
                    code="USER_UPDATE_ERROR", http_code=HTTP_403_FORBIDDEN, msg="You can't change user's password."
                )

            is_superuser = validated_data.get("is_superuser", Empty)
            if is_superuser is not Empty and instance.is_superuser != is_superuser:
                raise AdcmEx(
                    code="USER_UPDATE_ERROR",
                    http_code=HTTP_403_FORBIDDEN,
                    msg=f"You can't {'grant' if is_superuser else 'withdraw'} ADCM Administrator's rights.",
                )

        return update_user(
            user=instance,
            context_user=context_user,
            partial=self.partial,
            need_current_password=False,
            **validated_data,
        )

    def create(self, validated_data):
        context_user = self.context["request"].user

        if not context_user.is_superuser and validated_data["is_superuser"]:
            raise AdcmEx(
                code="USER_CREATE_ERROR",
                http_code=HTTP_403_FORBIDDEN,
                msg="You can't create user with ADCM Administrator's rights.",
            )

        return create_user(**validated_data)


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
