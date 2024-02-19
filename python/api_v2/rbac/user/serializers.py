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
from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from rbac.models import User
from rest_framework.fields import (
    BooleanField,
    CharField,
    EmailField,
    IntegerField,
    ListField,
    RegexField,
    SerializerMethodField,
)
from rest_framework.serializers import ModelSerializer

from api_v2.rbac.user.constants import UserStatusChoices

BLOCKED_MANUALLY_MESSAGE = "Unlimited block: manual block by ADCM Administrator"
BLOCKED_BY_BRUT_FORCE_PROTECTION = "Brute-force block: failure login attempt limit exceeded"


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
    blocking_reason = SerializerMethodField()
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
            "blocking_reason",
        ]

    @staticmethod
    def get_status(instance: User) -> str:
        if instance.is_active and instance.blocked_at is None:
            return UserStatusChoices.ACTIVE.value

        return UserStatusChoices.BLOCKED.value

    @staticmethod
    def get_blocking_reason(instance: User) -> str | None:
        if not instance.is_active:
            return BLOCKED_MANUALLY_MESSAGE

        if instance.blocked_at is not None:
            return BLOCKED_BY_BRUT_FORCE_PROTECTION

        return None


class UserUpdateSerializer(ModelSerializer):
    password = CharField(trim_whitespace=False, write_only=True, required=False)
    first_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False)
    last_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, required=False)
    email = EmailField(allow_blank=True, required=False)
    is_super_user = BooleanField(source="is_superuser", required=False)
    groups = ListField(child=IntegerField(), required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "password", "first_name", "last_name", "groups", "email", "is_super_user"]


class UserCreateSerializer(UserUpdateSerializer):
    username = RegexField(r"^[^\s]+$", max_length=settings.USERNAME_MAX_LENGTH)
    password = CharField(trim_whitespace=False, write_only=True)
    first_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, default="")
    last_name = RegexField(r"^[^\n]*$", max_length=150, allow_blank=True, default="")
    email = EmailField(allow_blank=True, default="")
    is_super_user = BooleanField(source="is_superuser", default=False)
    groups = ListField(child=IntegerField(), required=False, allow_null=True)

    class Meta:
        model = User
        fields = ["username", "password", "first_name", "last_name", "groups", "email", "is_super_user"]
