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

from api_v2.rbac.groups.serializers import GroupNameSerializer
from api_v2.rbac.users.constants import UserStatusChoices
from rbac.models import User
from rest_framework.fields import (
    BooleanField,
    CharField,
    EmailField,
    JSONField,
    RegexField,
    SerializerMethodField,
)
from rest_framework.serializers import ModelSerializer

from adcm.serializers import IdSerializer


class UserSerializer(ModelSerializer):
    status = SerializerMethodField()
    is_built_in = BooleanField(read_only=True, source="built_in")
    groups = GroupNameSerializer(many=True)

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
            "is_superuser",
            "groups",
        ]

    @staticmethod
    def get_status(instance: User) -> str:
        if instance.blocked_at is None:
            return UserStatusChoices.ACTIVE.value

        return UserStatusChoices.BLOCKED.value


class UserUpdateSerializer(ModelSerializer):
    password = CharField(trim_whitespace=False, write_only=True, required=False)
    current_password = CharField(trim_whitespace=False, write_only=True, required=False)
    first_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False, default="")
    last_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False, default="")
    groups = IdSerializer(many=True, required=False)
    email = EmailField(allow_blank=True, required=False, default="")
    is_superuser = BooleanField(required=False)

    class Meta:
        model = User
        fields = ["id", "password", "current_password", "first_name", "last_name", "groups", "email", "is_superuser"]


class UserCreateSerializer(UserUpdateSerializer):
    username = RegexField(r"^[^\s]+$", max_length=150)
    password = CharField(trim_whitespace=False, write_only=True)
    first_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, default="")
    last_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, default="")
    groups = IdSerializer(many=True, allow_null=True, required=False)
    email = EmailField(allow_blank=True, default="")
    is_superuser = BooleanField(default=False)
    profile = JSONField(required=False, default="")

    class Meta:
        model = User
        fields = ["id", "username", "password", "first_name", "last_name", "groups", "email", "is_superuser", "profile"]
