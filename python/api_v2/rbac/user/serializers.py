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

from api_v2.rbac.user.constants import UserStatusChoices
from django.contrib.auth.models import Group as AuthGroup
from rbac.models import User
from rest_framework.fields import (
    BooleanField,
    CharField,
    EmailField,
    RegexField,
    SerializerMethodField,
)
from rest_framework.serializers import ModelSerializer


class RelatedGroupSerializer(ModelSerializer):
    display_name = SerializerMethodField()

    class Meta:
        model = AuthGroup
        fields = ["id", "name", "display_name"]

    @staticmethod
    def get_display_name(instance: AuthGroup) -> str:
        return instance.group.display_name


class UserSerializer(ModelSerializer):
    status = SerializerMethodField()
    is_built_in = BooleanField(read_only=True, source="built_in")
    groups = RelatedGroupSerializer(many=True)
    is_super_user = BooleanField(read_only=True, source="is_superuser")

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "status",
            "email",
            "type",
            "is_built_in",
            "is_super_user",
            "groups",
        ]

    @staticmethod
    def get_status(instance: User) -> str:
        if instance.blocked_at is None:
            return UserStatusChoices.ACTIVE.value

        return UserStatusChoices.BLOCKED.value


class UserUpdateSerializer(ModelSerializer):
    password = CharField(trim_whitespace=False, write_only=True, required=False)
    first_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False)
    last_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False)
    email = EmailField(allow_blank=True, required=False)
    is_super_user = BooleanField(source="is_superuser", required=False)

    class Meta:
        model = User
        fields = ["id", "password", "first_name", "last_name", "groups", "email", "is_super_user"]


class UserCreateSerializer(UserUpdateSerializer):
    username = RegexField(r"^[^\s]+$", max_length=150)
    password = CharField(trim_whitespace=False, write_only=True)
    first_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, default="")
    last_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, default="")
    email = EmailField(allow_blank=True, default="")
    is_super_user = BooleanField(source="is_superuser", default=False)

    class Meta:
        model = User
        fields = ["username", "password", "first_name", "last_name", "groups", "email", "is_super_user"]
