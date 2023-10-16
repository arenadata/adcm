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
from cm.models import ADCM, ConfigLog
from rbac.models import User
from rest_framework.fields import CharField, SerializerMethodField
from rest_framework.serializers import BooleanField, ModelSerializer


class ProfileSerializer(ModelSerializer):
    is_super_user = BooleanField(source="is_superuser", read_only=True)
    auth_settings = SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_super_user",
            "auth_settings",
        ]
        read_only_fields = ["username", "email", "first_name", "last_name", "is_super_user", "auth_settings"]

    @staticmethod
    def get_auth_settings(user: User) -> dict:  # pylint: disable=unused-argument
        adcm = ADCM.objects.first()
        auth_policy = ConfigLog.objects.filter(obj_ref=adcm.config).last().config["auth_policy"]
        auth_settings = {
            "minPasswordLength": auth_policy["min_password_length"],
            "maxPasswordLength": auth_policy["max_password_length"],
            "loginAttemptLimit": auth_policy["login_attempt_limit"],
            "blockTime": auth_policy["block_time"],
        }
        return auth_settings


class ProfileUpdateSerializer(ModelSerializer):
    new_password = CharField(trim_whitespace=False, required=False, write_only=True, source="password")
    current_password = CharField(trim_whitespace=False, required=False, write_only=True)

    class Meta:
        model = User
        fields = [
            "new_password",
            "current_password",
        ]
